**************
Rsync deployer
**************

Rsync deployer uses ``rsync`` to deploy software.
The configuration needs to include at least::

  - method: 'rsync'
    target_host: 'user@server'
    source: '/path/to/installation'
    dest: '/path/to/installation'

Other optional parameters are: 

- ``working_directory: '/path/to/working_directory'`` *default:* **None**. A parameter that can be used to give the working directory for the rsync command in a case where relative paths need to be used instead of absolute paths.
- ``delete: True/False`` *default:* **False**. If set **True**, rsync deletes extraneous files from the dest dir.
- ``rsync_flags: '[flags]'`` *default: '-surlptDxv'*.
- ``ssh_command: '[command]'`` *default: ssh*. The ssh command for rsync.
- ``set_sbit: True/False`` *default:* **False**. If set **True**, sets sbit for the rsynced files and directories.
