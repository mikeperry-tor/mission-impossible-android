"""
Use the help command to get more information about other commands.

Usage:
  mia help <command>

"""

# Import custom helpers.
from mia.helpers.utils import *


def main():
    # Get the MIA handler singleton.
    handler = MiaHandler()

    # TODO: Find a dynamic way to import the right command.
    #       getattr() does not work on sub-module that were not imported.
    import mia.commands.clean
    import mia.commands.definition

    # Get the command name.
    command_name = handler.args['<command>']

    # Check if the command exists.
    if not hasattr(mia.commands, command_name):
        print('No such command: %s' % command_name)
        return None

    # Retrieve the command information.
    command_info = getattr(mia.commands, command_name)

    if command_info.__doc__ is None:
        print('No documentation is available for: %s' % command_name)
        return None

    # Print the command documentation.
    print(command_info.__doc__.lstrip())