/** @odoo-module **/

import { registry } from "@web/core/registry";
import { InvalidLicenseDialog } from "./components/InvalidLicenseDialog";
import { showDialog } from "@web/core/dialog/dialog";
import {InvalidLicenseDialog } from "../components/InvalidLicenseDialog";

registry.category("action_service").add("vex_soluciones_license_validator", async function(env, action) {
    const instances = await env.services.orm.searchRead("vex.instance", [
        ["license_valid_str", "!=", "active"],
        ["store_type", "=", "mercadolibre"],
    ], ["id"]);

    if (instances.length > 0) {
        showDialog({
            Component: InvalidLicenseDialog,
            props: {},
        });
        return;
    }
});
