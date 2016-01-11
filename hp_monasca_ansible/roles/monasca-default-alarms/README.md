# monasca-default-alarms

This role will setup a default alarm definition configuration for Monasca. It also provides an Ansible module for creation
of Monasca alarm definitions and notifications. More details on alarm definitions can be found at the
[Monasca API documentation](https://github.com/stackforge/monasca-api/blob/master/docs/monasca-api-spec.md#alarm-definitions-and-alarms)

##Requirements
It is assumed the service endpoint for Monasca is properly registered in keystone.

##Role Variables

These variables must be defined.

- keystone_url
- monasca_keystone_user
- monasca_keystone_password

By default the configured alarm definitions will be setup with a notification to root@localhost change the `default_email` variable to modify.

## Example Playbook

    - name: Define default alarm definitions
      hosts: mini-mon
      gather_facts: no
      vars:
        keystone_url: http://192.168.10.5:35357/v3/
        monasca_keystone_user: mini-mon
        monasca_keystone_password: password
      roles:
        - {role: monasca-default-alarms, tags: [alarms]}

## Monasca Modules Usage
There are two modules available in the library subdirectory, one for Monasca notifications and the other for alarm definitions. For example:

    - name: Setup default email notification method
      monasca_notification_method:
        name: "Default Email"
        type: 'EMAIL'
        address: "root@localhost"
        keystone_url: "{{keystone_url}}"
        keystone_user: "{{monasca_keystone_user}}"
        keystone_password: "{{monasca_keystone_password}}"
        keystone_project: "{{monasca_keystone_project}}"
      register: default_notification
    - name: Host Alive Alarm
      monasca_alarm_definition:
        name: "Host Alive Alarm"
        description: "Trigger when a host alive check fails"
        expression: "host_alive_status > 0"
        monasca_keystone_token: "{{default_notification.keystone_token}}"
        monasca_api_url: "{{default_notification.monasca_api_url}}"
        severity: "HIGH"
        alarm_actions:
          - "{{default_notification.notification_method_id}}"
        ok_actions:
          - "{{default_notification.notification_method_id}}"
        undetermined_actions:
          - "{{default_notification.notification_method_id}}"

Refer to the documentation within the module for full detail


##License
Apache

##Author Information
Tim Kuhlman
Monasca Team email monasca@lists.launchpad.net
