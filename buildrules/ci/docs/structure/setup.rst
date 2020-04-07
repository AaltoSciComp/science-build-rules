=====
Setup
=====

**************************
Requirements
**************************

The system you're using for the build system should have the following:

1. ``docker``
2. ``docker-compose``

**************************
Installation
**************************

Setting up SBE is done with science build rules, with a builder designed for the job.   

1. Clone ``science-build-rules``-repository and go through its installation steps.

2. In ``science-build-rules``: modify :file:`configs/ci/build_config.yaml` to match your system and needs. 

    .. container:: toggle

        .. container:: header

            **Build configuration file description:**

        The build configuration file :file:`configs/ci/build_config.yaml` contains all the necessary configurations to set up SBE. 

        For the passwords you can, for example, use :command:`pwgen 40 10`

        .. code-block:: yaml

        	# HERE'S AN EXAMPLE YAML WITH EXPLANATIONS AS VALUES
            build_environment_repository: # The repository to clone SBE from.
            science_build_rules_repository: # The repository that SBE will use to do builds.
            build_folder: # The location where SBE will be cloned into.
            compose_project_name: # Compose project name.
            buidbot_master:  
                image: # Where to pull the buildbot master docker image from. 
                fqdn: # Fully qualified domain name. 
                gitlab_hook_secret:
                worker_password:
                worker_port:
                web_port: # The port for web interface.
                timeout: 
                worker_uid: # This should be the uid of the user that runs SBE. 
            auths: 
                ssh:
                    config_file:
                    known_hosts_file: 
                    private_keys:
                        - # key1
                        - # key2
                    public_keys:
                        - # key1.pub
                        - # key2.pub
                docker:
                    config_file: # Docker configuration file [NOT IN USE]
                singularity:
                    config_file: # Singularity configuration file [NOT IN USE]
            buildbot_db:
                postgres_password:
            builds: 
                singularity: 
                    enabled: # [NOT IMPLEMENTED]
                    enable_portus_hook: # [NOT IMPLEMENTED]
                spack:
                    enabled: # If True, enables Spack builds
                registry_clone:
                    enabled: # [NOT IMPLEMENTED]
            target_workers:
              - name: # Name for a worker container
                image: # Which image to use for the worker
                spack_target_path: 
              - name: # Name for another worker container
              	image: # Image for the other worker container
              	spack_target_path:  



3. In ``science-build-rules``: :command:`python3 -m buildrules ci build configs/ci`

4. Make sure the ssh keys in :file:`science-build-environment/nfs/buildbot_home/nfs/.ssh` have access to the ``science-build-rules``-repository.

**************************
Activation
**************************

1. Navigate to the ``science-build-environment``-directory that was created with ``science-build-rules``, there:

2. :command:`sudo modprobe nfsd`

3. :command:`docker-compose up`