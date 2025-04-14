/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { jsonrpc } from "@web/core/network/rpc_service";

class InstanceSelector extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.state = useState({
            instances: [],
            selectedInstance: "all",
        });

        onMounted(async () => {
            this.getVexInstances();
        });
    }
    
    async getVexInstances (){
        let datos = await jsonrpc('/web/dataset/call_kw', {
            model: 'vex.instance',
            method: 'get_instances',
            args: [],
            kwargs: {}
        });
        
        console.log("INSTANCES",datos) ;
        this.state.instances = datos;
    }

    onInstanceChange(event) {
        this.state.selectedInstance = event.target.value;
        console.log("Instance Selected:", this.state.selected_instance);
    }
}

InstanceSelector.template = "vex_sync_mercado_libre.instance_selector_template";

registry.category("main_components").add("InstanceSelector", {
    Component: InstanceSelector,
    props: {},
});