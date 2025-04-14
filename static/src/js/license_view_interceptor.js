/** @odoo-module **/

import { registry } from "@web/core/registry";
import { InvalidLicenseDialog } from "../components/InvalidLicenseDialog";
import { showDialog } from "@web/core/dialog/dialog";

const viewService = registry.category("services").get("view");

registry.category("services").add("vex_license_view_interceptor", {
    ...viewService,
    async loadView(env, viewType, viewId, options = {}) {
        const instances = await env.services.orm.searchRead("vex.instance", [
            ["license_valid_str", "!=", "active"],
            ["store_type", "=", "mercadolibre"],
        ], ["id"]);

        if (instances.length > 0) {
            showDialog({
                Component: InvalidLicenseDialog,
                props: {},
            });
            throw new Error("Licencia inválida. Acceso denegado.");
        }

        return viewService.loadView(env, viewType, viewId, options);
    },
});
