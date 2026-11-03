from ansible.module_utils.basic import AnsibleModule


def main():
    m = AnsibleModule(argument_spec={"who": {"type": "str", "required": True}})
    m.exit_json(changed=False, greeting="hello " + m.params["who"])
main()
