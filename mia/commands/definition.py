"""
Create and configure a definition in the current workspace using the provided
template.

Usage:
    mia definition create [--cpu=<cpu>] [--force] [--template=<template>]
                          [<definition>]
    mia definition configure <definition>
    mia definition lock [--force-latest] <definition>
    mia definition dl-apps <definition>
    mia definition dl-os <definition>
    mia definition extract-update-binary <definition>
    mia definition update-from-template <definition>
    mia definition --help

Available sub-commands:
    create                 Creates a definition.
    configure              Configures a definition.
    lock                   Creates a lock file for the applications.
    dl-apps                Downloads the applications using data from the lock file.
    dl-os                  Show information on how to download and verify an OS zip.
    extract-update-binary  Extract the update-binary from the CyanogenMod zip file.
    update-from-template   Update definition from template

Command options:
    --template=<template>  The template to use. [default: mia-default]
    --cpu=<cpu>            The device CPU architecture. [default: armeabi]
    --force                Delete existing definition.
    --force-latest         Force using the latest versions.


Notes:
    A valid <definition> name consists of lowercase letters, digits and hyphens.
    And it must start with a letter name.


"""

import re
import os
import shutil
import sys
import zipfile
import distutils.dir_util
import xml.etree.ElementTree as ElementTree

import yaml

# Import custom helpers.
from mia.helpers.android import MiaAndroid
from mia.helpers.fdroid import MiaFDroid
from mia.helpers.utils import MiaHandler
from mia.helpers.utils import MiaUtils


class Definition(object):
    def __init__(self):
        # Get the MIA handler singleton.
        self.handler = MiaHandler()

    def main(self):
        # The definition name is optional, this is helpful for new users.
        if self.handler.args['<definition>'] is None:
            msg = 'Please provide a definition name'
            self.handler.args['<definition>'] = MiaUtils.input_ask(msg)

        if not re.search(r'^[a-z][a-z0-9-]+$', self.handler.args['<definition>']):
            print('ERROR: Please provide a valid definition name! See: mia help definition')
            sys.exit(1)

        # Create the definition.
        if self.handler.args['create']:
            self.create_definition()
        elif not os.path.exists(self.handler.get_definition_path()):
            # Make sure the definition exists.
            print('ERROR: Definition "%s" does not exist!' %
                  self.handler.args['<definition>'])
            sys.exit(1)

        # Configure the definition.
        if self.handler.args['configure']:
            self.configure_definition()

        # Update definition from template.
        if self.handler.args['update-from-template']:
            self.update_definition()

        # Create the apps lock file.
        if self.handler.args['lock']:
            self.create_apps_lock_file()

        # Download the CyanogenMod OS.
        if self.handler.args['dl-os']:
            self.download_os()

        # Download apps.
        if self.handler.args['dl-apps']:
            self.download_apps()

        # Extract the update-binary from the CyanogenMod zip file.
        if self.handler.args['extract-update-binary']:
            self.extract_update_binary()

        return None

    def create_definition(self):
        definition_path = self.handler.get_definition_path()
        print('Destination directory is:\n - %s\n' % definition_path)

        # Make sure the definition does not exist.
        if os.path.exists(definition_path):
            if self.handler.args['--force']:
                print('Removing the old definition folder...')
                shutil.rmtree(definition_path)
            else:
                print('ERROR: Definition "%s" already exists!' %
                      self.handler.args['<definition>'])
                sys.exit(1)

        # Get the template name.
        template = self.handler.args['--template']
        template_path = self.handler.get_template_path(template)
        if template_path is None:
            print('ERROR: Template "%s" does not exist!' % template)
            sys.exit(1)

        print('Using template:\n - %s\n' % template_path)

        # Make sure the definitions folder exists.
        definitions_path = os.path.join(self.handler.get_workspace_path(), 'definitions')
        if not os.path.isdir(definitions_path):
            os.makedirs(definitions_path, mode=0o755)

        # Create the definition using the provided template.
        shutil.copytree(template_path, definition_path)

        # Configure the definition.
        if MiaUtils.input_confirm('Configure now?', True):
            self.configure_definition()

    def update_definition(self):
        definition_path = self.handler.get_definition_path()
        print('Destination directory is:\n - %s\n' % definition_path)

        settings = self.handler.get_definition_settings()
        template = settings['general']['template']
        template_path = self.handler.get_template_path(template)
        print('Using template:\n - %s\n' % template_path)

        # Check if the template exists.
        if not os.path.exists(template_path):
            print('ERROR: Template "%s" does not exist!' % template)
            sys.exit(1)

        # Create the definition using the provided template.
        distutils.dir_util.copy_tree(template_path, definition_path)

    def configure_definition(self):
        # Get the android device wrapper.
        android = MiaAndroid()

        # Detect the device codename.
        cm_device_codename = android.get_cyanogenmod_codename()
        print('Using device codename: %s\n' % cm_device_codename)

        # Detect the CyanogenMod release type.
        if MiaUtils.input_confirm('Use recommended CyanogenMod release type?', True):
            cm_release_type = android.get_cyanogenmod_release_type(True)
        else:
            cm_release_type = android.get_cyanogenmod_release_type(False)
        print('Using release type: %s\n' % cm_release_type)

        # Detect the CyanogenMod release version.
        if MiaUtils.input_confirm('Use recommended CyanogenMod release version?', True):
            cm_release_version = android.get_cyanogenmod_release_version(True)
        else:
            cm_release_version = android.get_cyanogenmod_release_version(False)
        print('Using release version: %s\n' % cm_release_version)

        # The path to the definition settings.yaml file.
        definition_path = self.handler.get_definition_path()
        settings_file = os.path.join(definition_path, 'settings.yaml')
        settings_file_backup = os.path.join(definition_path, 'settings.orig.yaml')

        # Create a backup of the settings file.
        shutil.copy(settings_file, settings_file_backup)

        # Update the settings file.
        MiaUtils.update_settings(settings_file, {'general': {
            'update': {
                'cm_device_codename': cm_device_codename,
                'cm_release_type': cm_release_type,
                'cm_release_version': cm_release_version,
            },
        }})

        # Create the apps lock file.
        self.create_apps_lock_file()

        # Download the CyanogenMod OS.
        if MiaUtils.input_confirm('Download CyanogenMod OS now?', True):
            self.download_os()

        # Download apps.
        if MiaUtils.input_confirm('Download apps now?', True):
            self.download_apps()

    # TODO: Implement the APK lock functionality.
    def create_apps_lock_file(self):
        # Get the APK lock data.
        lock_data = self.get_apps_lock_info()

        definition_path = self.handler.get_definition_path()
        lock_file_path = os.path.join(definition_path, 'apps_lock.yaml')
        print('Creating lock file:\n - %s\n' % lock_file_path)

        fd = open(lock_file_path, 'w')
        try:
            fd.write(yaml.dump(lock_data, default_flow_style=False))
            fd.close()
        except yaml.YAMLError:
            print('ERROR: Could not save the lock file!')
            sys.exit(1)
        finally:
            fd.close()

        # Download apps.
        if self.handler.args['lock'] and MiaUtils.input_confirm('Download apps now?', True):
            self.download_apps()

    def get_apps_lock_info(self):
        # Read the definition settings.
        settings = self.handler.get_definition_settings()

        if not settings['defaults']['repository_id']:
            print('Missing default repository id.')
            sys.exit(1)

        # Make sure the resources folder exists.
        resources_path = os.path.join(self.handler.get_workspace_path(), 'resources')
        if not os.path.isdir(resources_path):
            os.makedirs(resources_path, mode=0o755)

        # Download and read info from the index.xml file of all repositories.
        repositories_data = {}
        for repo_info in settings['repositories']:
            index_path = os.path.join(self.handler.get_workspace_path(), 'resources', repo_info['id'] + '.index.xml')

            if not os.path.isfile(index_path):
                index_url = '%s/%s' % (repo_info['url'], 'index.xml')
                print('Downloading the %s repository information from:\n - %s' % (repo_info['name'], index_url))
                MiaUtils.urlretrieve(index_url, index_path)

            # Parse the repository index file and return the XML root.
            xml_tree = ElementTree.parse(index_path)
            if not xml_tree:
                print('Error parsing file:\n - %s' % index_path)
            repo_info['tree'] = xml_tree.getroot()

            repositories_data[repo_info['id']] = repo_info

        apps_list = []
        warnings_found = False
        print('Looking for APKs:')
        for key, app_info in enumerate(settings['apps']):
            # Add app to list if download url was provided directly.
            if 'url' in app_info:
                lock_info = {
                    'id': app_info['id'],
                    'package_name': os.path.basename(app_info['url']),
                    'package_url': app_info['url'],
                }

                print(' - adding `%s`' % lock_info['id'])
                apps_list.append(lock_info)
                continue

            # Lookup the app by id and versioncode in the repository index.xml.
            if 'id' in app_info:
                # Use the default repository if no repo has been provided.
                if 'repo' not in app_info:
                    app_info['repo'] = settings['defaults']['repository_id']

                # Use the latest application version code.
                if self.handler.args['--force-latest'] or 'versioncode' not in app_info:
                    app_info['versioncode'] = 'latest'

                # Get the application info.
                lock_info = MiaFDroid.fdroid_get_app_lock_info(repositories_data, app_info)
                if lock_info is not None:
                    repo_id = lock_info['repository_id']
                    repo_name = repositories_data[repo_id]['name']
                    msg = ' - found `%s` in the %s repository.'
                    print(msg % (lock_info['id'], repo_name))
                    apps_list.append(lock_info)
                    continue

            warnings_found = True

        # Give the user a chance to fix any possible errors.
        if warnings_found and not MiaUtils.input_confirm('Warnings found! Continue?'):
            sys.exit(1)

        return apps_list

    def download_apps(self):
        # Read the definition apps lock data.
        lock_data = self.handler.get_definition_apps_lock_data()

        for apk_info in lock_data:
            print(' - downloading: %s' % apk_info['package_url'])
            download_dir = apk_info.get('path', 'user-apps')
            download_path = os.path.join(self.handler.get_definition_path(), download_dir)
            if not os.path.isdir(download_path):
                os.makedirs(download_path, mode=0o755)

            apk_path = os.path.join(download_path, apk_info['package_name'])
            cache_path = os.path.join(self.handler.get_workspace_path(), 'resources', 'apps')
            if not os.path.isdir(cache_path):
                os.makedirs(cache_path, mode=0o755)

            path, http_message = MiaUtils.urlretrieve(apk_info['package_url'], apk_path, cache_path)
            if http_message['status_code'] == 200:
                print('   - downloaded: %s' % MiaUtils.format_file_size(http_message['Content-Length']))
            elif http_message['status_code'] == 206:
                print('   - download continued: %s' % MiaUtils.format_file_size(http_message['Content-Length']))
            elif http_message['status_code'] == 416:
                print('   - already downloaded. Skipped.')
            else:
                raise Exception('   - error downloading file.')

    def download_os(self):
        """
        Display information to the user on how to download the OS and verify it's
        checksum.
        """
        print('\nNOTE: Command not finished yet; See instructions!\n')

        # Read the definition settings.
        settings = self.handler.get_definition_settings()

        # Create the resources folder.
        resources_path = os.path.join(self.handler.get_workspace_path(), 'resources')
        if not os.path.isdir(resources_path):
            os.makedirs(resources_path, mode=0o755)

        url = 'https://download.cyanogenmod.org/?device=%s&type=%s' % (
            settings['general']['cm_device_codename'],
            settings['general']['cm_release_type']
        )

        file_name = self.handler.get_os_zip_filename()

        message = '\n'.join((
            'Download CyanogenMod from:\n - %s',
            'and save the file as\n - %s',
            'into the resources folder, and remember to open a new terminal and',
            'verify the that provided md5 checksum matches the the output of:',
            ' ~$ md5sum resources/%s',
        ))
        print(message % (url, file_name, file_name))

        # Make sure the OS archive exists.
        zip_file_path = os.path.join(resources_path, file_name)
        while True:
            MiaUtils.input_pause('Please follow the instructions before continuing.')

            # Only allow the user to continue if the OS image exists.
            if os.path.isfile(zip_file_path):
                break

            # Display message and try again.
            print('File not found:\n - %s' % zip_file_path)

    def extract_update_binary(self):
        # Get the resources folder.
        resources_path = os.path.join(self.handler.get_workspace_path(), 'resources')

        definition_path = self.handler.get_definition_path()

        # Get file path.
        zip_file_path = os.path.join(resources_path, self.handler.get_os_zip_filename())

        # The path to the update-binary file inside the zip.
        update_relative_path = 'META-INF/com/google/android/update-binary'

        print('Extracting the update-binary from:\n - %s' % zip_file_path)

        if os.path.isfile(zip_file_path) and zipfile.is_zipfile(zip_file_path):
            # Extract the update-binary in the definition.
            fd = zipfile.ZipFile(zip_file_path)

            # Save the file; taken from ZipFile.extract
            source = fd.open(update_relative_path)
            destination = os.path.join(definition_path, 'other', 'update-binary')
            target = open(destination, 'wb')
            with source, target:
                shutil.copyfileobj(source, target)
            os.chmod(destination, 0o755)

            print('Saved the update-binary to the definition!')
        else:
            print('File does not exist or is not a zip file.')
