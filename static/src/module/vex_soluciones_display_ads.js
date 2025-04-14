/** @odoo-module **/

import { loadBundle, loadJS } from "@web/core/assets";
import { Component, onWillUnmount, useEffect, useRef, useState, onWillStart, onMounted  } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { jsonrpc } from "@web/core/network/rpc_service";
//import Chart from "chart.js/auto";


class DisplayADS extends Component {
    static template = "vex_sync_mercado_libre.display_ads";

    setup() {
        
        //Code to open view
        this.rpc = useService("rpc");  // Using the RPC service
        this.action = useService("action");  // Using the Action service to open the view

        self = this.action; // Ensure self is set in the constructor

        this.http = useService("http");
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notificationService = useService("notification");
        this.state = useState({
            title: "",
            campaigns :[],
            lineitems :[],

            startDateCampaigns: "", // Fecha de inicio seleccionada
            endDateCampaigns: "",
            filterTypeDateCamp: "7",
            filterTypeDateItems: "7",

            currentView: "table",
            selectedRecord: null,

            rowsPerPage: 10,
            currentPage_campaigns: 1,
            currentPage_lineitems: 1,
            
            filteredCampaigns: [],
            filtersCampaigns: {
                search: "",
                status: "",
            },
            
            activeMetricCamp: "clicks",
            activeMetricDetail: "clicks",

            filteredItems: [],
            filtersItems: {
                search: "",
                status: "",
                
            },

            column: "",
            items: [
                // { w: 2, h: 2, content: 'my first widget' }, 
                // { w: 2, content: 'another longer widget!' } 
            ]

        });
        
        onMounted(() => {
            this.renderChartCamp();
        });

        this.canvasRef = useRef("chartCampaign");
        this.canvasRef2 = useRef("chartDetail");

        this.chartCamp = null,  
        this.chartDetail = null;
               

        onWillStart(async () => {           
            await loadBundle("web.chartjs_lib");
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js")
        });

        onWillStart(async () => {            
            
        });

        useEffect(() => {
            const grid = GridStack.init({
                cellHeight: 'auto',
                animate: false, // show immediate (animate: true is nice for user dragging though)
                // columnOpts: {
                //     columnWidth: 100, // wanted width
                // },
            }).on('change', (ev, gsItems) => {
                this.column = grid.getColumn();
                console.log(this.column)
            });;

            grid.load(this.state.items);

            this.load_data();

        },() => []    
            );

        onWillUnmount(() => {
            this.onWillUnmount()
        });
    }

     async load_data(){
        this.fetchLatestCampaigns(this.state.filterTypeDateCamp).then(this.renderChartCamp);
        if (this.state.selectedRecord) {
            this.fetchLatestItems(this.state.filterTypeDateItems).then(this.renderChartDetail);
        }
        this.render();
    }

    async handleFilterChangeCamp() {
        await this.fetchLatestCampaigns(this.state.filterTypeDateCamp).then(this.updateChartCamp);

    }

    async handleFilterChangeItems() {
        await this.fetchLatestItems(this.state.filterTypeDateItems).then(this.updateChartDetail);
    }

    changeMetricCamp = (metric) => {
        this.state.activeMetricCamp = metric;
        this.updateChartCamp();
    }

    changeMetricDetail = (metric) => {
        this.state.activeMetricDetail = metric;
        this.updateChartDetail();
    }

    renderChartCamp = () => {
        if (this.chartCamp) {
            this.chartCamp.destroy();
        }
        this.chartCamp = new Chart(this.canvasRef.el, {
            type: "bar",
            data: this.getChartDataCamp(),
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        stacked: true,
                        grid: { display: true, color: "rgba(255,99,132,0.2)" }
                    },
                    x: {
                        grid: { display: false },
                        title: { display: true, text: "Campaigns" }
                    }
                }
            },
        });
    }

    renderChartDetail = () => {
        if (this.chartDetail) {
            this.chartDetail.destroy();
        }
        this.chartDetail = new Chart(this.canvasRef2.el, {
            type: "bar",
            data: this.getChartDataDetail(),
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        stacked: true,
                        grid: { display: true, color: "rgba(255,99,132,0.2)" }
                    },
                    x: {
                        grid: { display: false },
                        title: { display: true, text: "Line Items" }
                    }
                }
            },
        });
    }
    
    updateChartCamp = () => {
        if (this.chartCamp) {
            this.chartCamp.data = this.getChartDataCamp();
            this.chartCamp.update();
        }
    }

    updateChartDetail = () => {
        if (this.chartDetail) {
            this.chartDetail.data = this.getChartDataDetail();
            this.chartDetail.update();
        }
    }

    getChartDataCamp() {
        return {
            labels: this.state.filteredCampaigns.map(c => c.name),
            datasets: [{
                label: this.state.activeMetricCamp.toUpperCase(),
                data: this.state.filteredCampaigns.map(c => this.cleanValue(c[this.state.activeMetricCamp])),
                backgroundColor: "rgba(54, 162, 235, 0.5)",
                borderColor: "rgba(54, 162, 235, 1)",
                tension: 0.1
            }],
        };
    }

    getChartDataDetail() {
        return {
            labels: this.state.filteredItems.map(a => a.term),
            datasets: [{
                label: this.state.activeMetricDetail.toUpperCase(),
                data: this.state.filteredItems.map(a => this.cleanValue(a[this.state.activeMetricDetail])),
                backgroundColor: "rgba(54, 235, 211, 0.5)",
                borderColor: "rgb(54, 235, 190)",
                tension: 0.1
            }],
        };
    }

    cleanValue(value) {
        if (typeof value === "string") {
            return Number(value.replace(/[^0-9.]/g, "")) || 0;
        }
        return value;
    }

    async fetchLatestCampaigns (option){
        let datos = await jsonrpc('/web/dataset/call_kw', {
            model: 'vex.meli.display',
            method: 'get_latest_campaigns',
            args: [option],
            kwargs: {}
        });
        
        console.log("Latest Campaigns",datos) ;
        this.state.campaigns = datos;           
        this.applyFiltersCampaign();            
    }

    async fetchLatestItems (option){
        let datos = await jsonrpc('/web/dataset/call_kw', {
            model: 'vex.meli.display',
            method: 'get_latest_lineitems',
            args: [this.state.selectedRecord, option],
            kwargs: {}
        });
        
        console.log("Latest lineitems",datos) ;
        this.state.lineitems = datos;
        this.applyFiltersLineItems();                     
    }
    
    /* async test(){

        let datos = await jsonrpc('/web/dataset/call_kw', {
            model: 'vex.meli.display',
            method: 'get_latest_lineitems',
            args: ['83398', '90'],
            kwargs: {}
        });
        
        console.log("get_data_from_meli",datos) ;

    } */

    openRecord(event) {
        if (this.chartCamp) {
            this.chartCamp.destroy(); // Destruir gráfico actual si existe
            this.chartCamp = null;
        }
        if (this.chartDetail) {
            this.chartDetail.destroy(); // Destruir gráfico actual si existe
            this.chartDetail = null;
        }
        const recordId = event.currentTarget.dataset.id;
        this.state.selectedRecord = recordId;
        console.log("GFFgG", this.state.selectedRecord)
        this.state.currentView = "detail";
        setTimeout(() => {
            this.load_data();
        }, 100);
    }

    goBack = () => {
        if (this.chartDetail) {
            this.chartDetail.destroy(); // Destruir gráfico actual si existe
            this.chartDetail = null;
        }
        if (this.chartCamp) {
            this.chartCamp.destroy(); // Destruir gráfico actual si existe
            this.chartCamp = null;
        }
        this.state.currentView = "table";
        this.state.selectedRecord = null;
        setTimeout(() => {
            this.load_data();
        }, 100);
        //this.updateChartCamp();
    }

    get totalPagesCampaigns() {
        return Math.ceil(this.state.filteredCampaigns.length / this.state.rowsPerPage);
    }

    get paginatedCampaigns() {
        const start = (this.state.currentPage_campaigns - 1) * this.state.rowsPerPage;
        const end = start + this.state.rowsPerPage;
        return this.state.filteredCampaigns.slice(start, end);
    }

    nextPageCampaigns() {
        if (this.state.currentPage_campaigns < this.totalPagesCampaigns) {
            this.state.currentPage_campaigns++;
        }
    }

    prevPageCampaigns() {
        if (this.state.currentPage_campaigns > 1) {
            this.state.currentPage_campaigns--;
        }
    }

    get totalPages() {
        return Math.ceil(this.state.filteredItems.length / this.state.rowsPerPage);
    }

    get paginatedLineItems() {
        const start = (this.state.currentPage_lineitems - 1) * this.state.rowsPerPage;
        const end = start + this.state.rowsPerPage;
        return this.state.filteredItems.slice(start, end);
    }

    nextPageLineItems() {
        if (this.state.currentPage_lineitems < this.totalPagLineItems) {
            this.state.currentPage_lineitems++;
        }
    }

    prevPageLineItems() {
        if (this.state.currentPage_lineitems > 1) {
            this.state.currentPage_lineitems--;
        }
    }
    
    applyFiltersCampaign() {
        const { search, status } = this.state.filtersCampaigns;
        const searchLower = search.toString().toLowerCase();

        this.state.filteredCampaigns = this.state.campaigns.filter(record =>
            (search ? record.name.toLowerCase().includes(searchLower) : true) &&
            (status ? record.status === status : true)
        );

        this.state.currentPage_campaigns = 1;
        this.updateChartCamp();
    }

    updateFilterCampaign = (ev, filterKey) => {
        if (!ev || !ev.target) {
            console.error("Evento no definido:", ev);
            return;
        }
        this.state.filtersCampaigns[filterKey] = ev.target.value;
        this.applyFiltersCampaign();
    }

    applyFiltersLineItems() {
        const { search } = this.state.filtersItems;
        const searchLower = search.toString().toLowerCase();

        this.state.filteredItems = this.state.lineitems.filter(record =>
            (search ? record.term.toString().toLowerCase().includes(searchLower) : true)
        );

        this.state.currentPage_lineitems = 1;
        this.updateChartDetail();
    }

    updateFilterLineItems = (ev, filterKey) => {
        if (!ev || !ev.target) {
            console.error("Evento no definido:", ev);
            return;
        }
        this.state.filtersItems[filterKey] = ev.target.value;
        this.applyFiltersLineItems();
    }

    exportToExcelCampaigns() {
        if (this.state.filteredCampaigns.length === 0) {
            alert("No hay datos para exportar.");
            return;
        }

        let columnMap = {
            "name": "Name",
            "status": "Status",
            "budget": "Budget",
            "strategy": "Type Campaign",
            "acos_target": "ACOS Target",
            "advertising_items_quantity": "Advertising Sales",
            "prints": "Prints",
            "clicks": "Clics",
            "total_amount": "Income",
            "cost": "Cost",
            "acos": "ACOS",
        };

        let filteredData = this.state.filteredCampaigns.map(record => {
            let newRecord = {};
            Object.keys(columnMap).forEach(key => {
                newRecord[columnMap[key]] = record[key];
            });
            return newRecord;
        });

        let worksheet = XLSX.utils.json_to_sheet(filteredData);

        let workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, "Campaigns");

        XLSX.writeFile(workbook, "Campaigns.xlsx");
    }

    exportToExcelLineItems() {
        if (this.state.filteredItems.length === 0) {
            alert("No hay datos para exportar.");
            return;
        }
        
        let columnMap = {
            "term": "Term",
            "cpc_max": "CPC Max",
            "cpc": "Cost per Clic",
            "prints": "Prints",
            "clicks": "Clics",
            "units_quantity": "Sales",
            "cvr": "CVR",
            "units_amount": "Income",
            "ctr": "CTR",
            "consumed_budget": "Investment",
            "acos": "ACOS",
        };

        let filteredData = this.state.filteredItems.map(record => {
            let newRecord = {};
            Object.keys(columnMap).forEach(key => {
                newRecord[columnMap[key]] = record[key];
            });
            return newRecord;
        });

        let worksheet = XLSX.utils.json_to_sheet(filteredData);

        let workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, "LineItems");

        XLSX.writeFile(workbook, "LineItems.xlsx");
    }

    onWillUnmount() {
        if (this.chartCamp) {
            this.chartCamp.destroy();
        }
        if (this.chartDetail) {
            this.chartDetail.destroy();
        }
    }
}

registry.category("actions").add("vex_sync_mercado_libre.display_ads", DisplayADS);


