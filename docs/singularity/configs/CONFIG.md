# SingularityAaltoCI configuration

All configuration is organized based on targets. So if build target is centos,
it has its configuration stored in a folder called centos. An image with the
same tag should be present in 
[singularity-builder-images](https://hub.docker.com/r/aaltoscienceit/singularity-builder-images).

## Image configuration

The desired images are specified in **versions.yaml**. Each image has the
following structure:

```yaml
singularity_versions:
  - docker_name: 'tensorflow'
    docker_tags:
      - '1.4.1-gpu'
    dockerhub_user: 'tensorflow'
    module_name: 'singularity-tensorflow'
    flag_collections:
      - 'common'
      - 'nvidia'
    command_collections:
      - 'common'
    alias:
      python: 'singularity_wrapper exec python'
      ipython: 'singularity_wrapper exec ipython'
```

- `docker_name` specifies the Docker image name.
- `docker_tags` is a list that specifies which Docker tags we want to use. Each
tag will create its own image/module file.
- `dockerhub_user` specifies the DockerHub user name that owns the image.
- `module_name` is an optional argument that specifies the desired name for 
the module file. By default the name is `singularity-{docker_name}`. Version 
is always the tag.
- `flag_collections` is a list of strings that specifies which flags should be 
given to `singularity_wrapper`. More on this below.
- `command_collections` is a list of strings that specifies which commands
should be added to definition file. More on this below.
- `alias` is an optional dictionary of alias-command pairs that can be used to 
create a custom alias for some program in the image. In the example, after
loading the module, the user can simply run `python` to run `python`
interpreter in the image. All arguments given to the alias are provided to the
command.
- `registry` is an optional flag that determines different registry than
default Docker Hub registry. Check the **secrets.yaml** chapter on how to set
up authentication tokens.

There are two types of extra configurations that are written in
**versions.yaml**: `flag_collections` and `command_collections`.

`flag_collections` are used to provide flags to singularity during
runtime. These are written into the module file in environment variable
`SING_FLAGS`. This is used by `singularity_wrapper` to automatically bind
folders etc.

Example of `flag_collections` is provided below:

```yaml
flag_collections:
  common:
    - '-B /m:/m'
    - '-B /l:/l'
    - '-B /scratch:/scratch'
  nvidia:
    - '--nv'
```

In this example an image with `common` in its `flag_collections` would mount
`/m`-, `/l`- and `/scratch`-drives and an image with `nvidia` would mount the
nvidia drivers.

`command_collections` add commands to the singularity definition file. 
Documentation of these files is provided in
[here](http://singularity.lbl.gov/docs-recipes).

Example of `command_collections` is provided below:

```yaml
command_collections:
  common:
    post_commands:
      - 'mkdir /u'
      - 'for i in $(seq 0 9); do for j in $(seq 0 9) ; do ln -s /m/home/home$i/$i$j /u/$i$j ; done ; done'
      - 'mkdir /scratch'
      - 'mkdir /m'
      - 'mkdir /l'
      - 'mkdir /share'
```

In this example an image with `common` in its `command_collections` would add
the commands listed in `post_commands` to the `post`-section of the singularity
definition. In this case it would create mountpoints to various folders. Each
element of these lists is added as is so they can be whatever shell commands
you want.

Currently possible options are `environment_command`, `setup_commands`, `runscript_commands` and
`post_commands`.

## Install path configuration

**config.yaml** determines the path where the automation will install the
images.

`images_prefix` specifies the directory where the images are installed. This 
should be of the form `<sw target folder>/images`. 

`modules_prefix` specifies the directory where the modules are installed. This
should be of the form `<sw target folder>/modules`.

You should make sure that the resulting **folders are empty** and owned by the 
building user (triton-ci). It is a good idea to create them beforehand to
target system.

## Secret tokens for registry authentication

If you have a registry that requires authentication tokens you can place them
in **/singularity-ci/home/secrets.yaml** in `exoti.cs.aalto.fi`. The form of the
configuration file is

```yaml
secrets:
  nvcr.io:
    username: 'username'
    password: 'password'
```

This would provide username `username` and password `password` to registry 
`nvcr.io`.

## Deployment configuration

Deployment configuration is done in **deployconfig.yaml**. It has information
on how to deploy the software. Configuration looks like this:
```yaml
config:
  method: 'rsync'
  delete: True
  target_host: 'triton.aalto.fi'
  sources:
    - 'images_prefix'
    - 'modules_prefix'
```

Currently `rsync` is the only supported configuration method. `delete`
specifies whether `--delete` should be included in the rsync flags. 
`target_host` is self-evident. `sources` contains a list of folders to copy.
These folders are specified in **config.yaml**. Currently only `images_prefix`
and `modules_prefix` are supported.
