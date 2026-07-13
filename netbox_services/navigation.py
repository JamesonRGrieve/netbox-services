# SPDX-License-Identifier: AGPL-3.0-or-later
from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem


def _item(model, label):
    return PluginMenuItem(
        link=f"plugins:netbox_services:{model}_list",
        link_text=label,
        buttons=[PluginMenuButton(f"plugins:netbox_services:{model}_add", "Add", "mdi mdi-plus-thick")],
    )


menu = PluginMenu(
    label="Services",
    groups=(
        (
            "Catalog",
            (
                _item("servicecatalog", "Service Catalog"),
                _item("catalogcredential", "Credentials"),
                _item("catalogtoken", "Tokens"),
                _item("catalogsecondaryport", "Secondary Ports"),
                _item("integrationcatalog", "Integration Catalog"),
                _item("integrationcatalogparam", "Integration Catalog Params"),
                _item("catalogconfigparam", "Config Params"),
                _item("catalogextension", "Extensions"),
            ),
        ),
        (
            "Test Matrix",
            (
                _item("catalogteststate", "Test States"),
                _item("catalogtestintegration", "Test Integrations"),
            ),
        ),
        (
            "Instances",
            (
                _item("serviceinstance", "Service Instances"),
                _item("instanceopenbaopath", "OpenBao Paths"),
                _item("serviceinstanceconfigvalue", "Config Values"),
                _item("serviceinstanceextension", "Extensions"),
            ),
        ),
        (
            "Edges",
            (
                _item("integration", "Integrations"),
                _item("integrationparam", "Integration Params"),
                _item("hamirror", "HA Mirrors"),
            ),
        ),
        (
            "Host Roles",
            (
                _item("hostrole", "Host Roles"),
                _item("hostroleparam", "Host Role Params"),
                _item("hostroleassignment", "Host Role Assignments"),
                _item("hostroleassignmentvar", "Assignment Vars"),
            ),
        ),
    ),
    icon_class="mdi mdi-application-cog",
)
