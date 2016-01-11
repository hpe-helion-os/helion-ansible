#monasca-agent
Installs the [monasca-agent](https://github.com/stackforge/monasca-agent) part of the [Monasca](https://wiki.openstack.org/wiki/Monasca) project.
It is installs it into a virtualenv on the box.

## Requirements
virtualenv must be installed on the system.

- keystone_url:
- monasca_agent_user:
- monasca_agent_password:
- monasca_agent_project:

## Optional
- monasca_agent_check_frequency - Sets how often the collection run for the agent will occur
- monasca_agent_detection_args - Sets detection arguments during the monasca-setup run.
- monasca_agent_system_only - setting to true will cause Monasca setup to run in system_only mode
- monasca_agent_service:
- monasca_agent_dimensions: 'role:monitoring,region:a'
- monasca_api_url: if undefined it will be pulled from the keystone service catalog.
- monasca_agent_version: Defines a specific version to install, defaults to latest
- monasca_log_level: Log level of the agent logs, default is WARN
- pip_index_url: Index URL to use instead of the default for installing pip packages
- run_mode: One of Deploy, Stop, Install, Start, or Use. The default is Deploy which will do Install, Configure, then Start. 'Use' can be set if the only desire is to use the monasca_agent_plugin module

Optionally supply monasca_checks variable which is a dictionary with each entry consisting of a plugin name followed by the
plugin config, typically with two sections init_config and instances. Refer to the specific monasca-agent plugin documentation
for more detail.

An example ssh check:

    monasca_checks:
      host_alive:
        init_config:
          ssh_port: 22
          ssh_timeout: 0.5
          ping_timeout: 1
        instances:
          - devstack:
              name: devstack
              host_name: 192.168.10.5
              alive_test: ssh

## monasca_agent_plugin module
This role contains the module monasca_agent_plugin which can be used to run monasca-setup for specific detection plugins. This is particularily
useful when used with the monasca_agent_system_only option of the role. In a deployment of many machines every machine can have the role applied
in system only mode then as different services are installed they can selectively enable different agent plugins using this module. Example usage:

    - name: Monasca agent ntp plugin configuration
      monasca_agent_plugin: name="ntp"
    - name: Monasca agent plugin configuration
      monasca_agent_plugin:
        names:
            - ntp
            - mysql

You must have the monasca-agent role in your playbook. If the agent is already deployed and you just need to use monasca_agent_plugin, then you can add the role in and have it skip all install, configure and start steps by using these lines in your playbook:

  roles:
    - {role: monasca-agent, run_mode: Use}

To copy custom detection and/or check plugins to the machine before running the monasca_agent_plugin module, use the
[copy module](http://docs.ansible.com/copy_module.html) with the published variables `monasca_agent_check_plugin_dir` or `monasca_agent_detection_plugin_dir`
for example:

    - name: Copy example check plugin
      copy: src=files/check/example.py dest="{{monasca_agent_check_plugin_dir}}"
    - name: Copy example detection plugin
      copy: src=files/detection/example.py dest="{{monasca_agent_detection_plugin_dir}}"
    - name: Run Monasca agent example plugin configuration
      monasca_agent_plugin: name="example"

##License
Apache

##Author Information
Tim Kuhlman
Monasca Team email monasca@lists.launchpad.net
