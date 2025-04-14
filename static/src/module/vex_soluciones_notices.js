/** @odoo-module **/

import { loadBundle, loadJS } from "@web/core/assets";
import { Component, onMounted, onWillUnmount, useRef, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { jsonrpc } from "@web/core/network/rpc_service";

class NoticesTemplate extends Component {
    static template = "vex_sync_mercado_libre.notices";

    async setup() {
        this.rpc = useService("rpc");  // Using the RPC service
        this.action = useService("action");  // Using the Action service to open the view

        self = this.action; // Ensure self is set in the constructor

        this.http = useService("http");
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notificationService = useService("notification");
        this.state = useState({
            title: "",
            description: "",
            dataPublications: [],
            //dataPublications: [],
            filterByDate: "last_7",
            startDate: "",
            endDate: "",
            showDateFilter: false,
        });

        onWillStart(async () => {
            
        });

        //onWillUnmount(() => { this.onWillUnmount() });
    }

    async test(){

        let datos = await jsonrpc('/web/dataset/call_kw', {
            model: 'vex.meli.notices',
            method: 'get_data_from_meli',
            args: [],
            kwargs: {}
        });
        
        console.log("get_data_from_meli",datos) ;

    }

    async applyDateFilter(){

    }

    async handleFilterChange(){

    }
    mounted() {

    }

    onWillUnmount() {

    }


}

registry.category("actions").add("vex_sync_mercado_libre.notices", NoticesTemplate);


