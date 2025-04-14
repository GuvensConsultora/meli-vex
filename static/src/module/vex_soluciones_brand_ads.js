/** @odoo-module **/

import { loadBundle, loadJS } from "@web/core/assets";
import { Component, onWillUnmount, useEffect, useRef, useState, onWillStart, onMounted  } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { jsonrpc } from "@web/core/network/rpc_service";
//import Chart from "chart.js/auto";


class BrandADS extends Component {
    static template = "vex_sync_mercado_libre.brand_ads";

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
            keywords :[],

            startDateCampaigns: "", // Fecha de inicio seleccionada
            endDateCampaigns: "",
            filterTypeDateCamp: "7",
            filterTypeDateKeyw: "7",

            currentView: "table",
            selectedRecord: null,

            rowsPerPage: 10,
            currentPage_campaigns: 1,
            currentPage_keywords: 1,
            
            filteredCampaigns: [],
            filtersCampaigns: {
                search: "",
                status: "",
            },
            
            activeMetricCamp: "clicks",
            activeMetricDetail: "clics",

            filteredKeywords: [],
            filtersKeywords: {
                search: "",
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
            this.fetchLatestKeywords(this.state.filterTypeDateKeyw).then(this.renderChartDetail);
        }
        this.render();
    }

    async handleFilterChangeCamp() {
        await this.fetchLatestCampaigns(this.state.filterTypeDateCamp).then(this.updateChartCamp);

    }

    async handleFilterChangeKey() {
        await this.fetchLatestKeywords(this.state.filterTypeDateKeyw).then(this.updateChartDetail);
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
                        title: { display: true, text: "Keywords" }
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

    mappingMetrics(){
        if (this.state.activeMetricCamp == 'units_amount') {
            return 'INCOME'
        } else if (this.state.activeMetricCamp == 'units_quantity') {
            return 'SALES'
        } else if (this.state.activeMetricCamp == 'consumed_budget') {
            return 'COST'
        } else if (this.state.activeMetricCamp == 'clicks') {
            return 'CLICS'
        } else if (this.state.activeMetricCamp == 'acos') {
            return 'ACOS'
        } else if (this.state.activeMetricCamp == 'prints') {
            return 'PRINTS'
        } else if (this.state.activeMetricCamp == 'cpc') {
            return 'CPC'
        }
    }

    mappingMetricsKeys(){
        if (this.state.activeMetricDetail == 'units_amount') {
            return 'INCOME'
        } else if (this.state.activeMetricDetail == 'units_quantity') {
            return 'SALES'
        } else if (this.state.activeMetricDetail == 'consumed_budget') {
            return 'COST'
        } else if (this.state.activeMetricDetail == 'clics') {
            return 'CLICS'
        } else if (this.state.activeMetricDetail == 'acos') {
            return 'ACOS'
        } else if (this.state.activeMetricDetail == 'prints') {
            return 'PRINTS'
        } else if (this.state.activeMetricDetail == 'cpc') {
            return 'CPC'
        }
    }

    getChartDataCamp() {
        return {
            labels: this.state.filteredCampaigns.map(c => c.name),
            datasets: [{
                label: this.mappingMetrics(),
                data: this.state.filteredCampaigns.map(c => this.cleanValue(c[this.state.activeMetricCamp])),
                backgroundColor: "rgba(54, 162, 235, 0.5)",
                borderColor: "rgba(54, 162, 235, 1)",
                tension: 0.1
            }],
        };
    }

    getChartDataDetail() {
        return {
            labels: this.state.filteredKeywords.map(a => a.term),
            datasets: [{
                label: this.mappingMetricsKeys(),
                data: this.state.filteredKeywords.map(a => this.cleanValue(a[this.state.activeMetricDetail])),
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
            model: 'vex.meli.bads',
            method: 'get_latest_campaigns',
            args: [option],
            kwargs: {}
        });
        
        console.log("Latest Campaigns",datos) ;
        this.state.campaigns = datos;           
        this.applyFiltersCampaign();            
    }

    async fetchLatestKeywords (option){
        let datos = await jsonrpc('/web/dataset/call_kw', {
            model: 'vex.meli.bads',
            method: 'get_latest_keywords',
            args: [this.state.selectedRecord, option],
            kwargs: {}
        });
        
        console.log("Latest keywords",datos) ;
        this.state.keywords = datos;
        this.applyFiltersKeyword();                     
    }
    
    /* async test(){

        let datos = await jsonrpc('/web/dataset/call_kw', {
            model: 'vex.meli.bads',
            method: 'get_latest_keywords',
            args: ['32943', '90'],
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

    get totalPagesKeywords() {
        return Math.ceil(this.state.filteredKeywords.length / this.state.rowsPerPage);
    }

    get paginatedKeywords() {
        const start = (this.state.currentPage_keywords - 1) * this.state.rowsPerPage;
        const end = start + this.state.rowsPerPage;
        return this.state.filteredKeywords.slice(start, end);
    }

    nextPageKeywords() {
        if (this.state.currentPage_keywords < this.totalPagesKeywords) {
            this.state.currentPage_keywords++;
        }
    }

    prevPageKeywords() {
        if (this.state.currentPage_keywords > 1) {
            this.state.currentPage_keywords--;
        }
    }
    
    applyFiltersCampaign() {
        const { search, status } = this.state.filtersCampaigns;
        const searchLower = search.toString().toLowerCase();

        this.state.filteredCampaigns = this.state.campaigns.filter(record =>
            (search ? (record.name.toLowerCase().includes(searchLower) || 
                       record.strategy.toLowerCase().includes(searchLower)) : true) &&
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

    applyFiltersKeyword() {
        const { search } = this.state.filtersKeywords;
        const searchLower = search.toString().toLowerCase();

        this.state.filteredKeywords = this.state.keywords.filter(record =>
            (search ? record.term.toString().toLowerCase().includes(searchLower) : true)
        );

        this.state.currentPage_keywords = 1;
        this.updateChartDetail();
    }

    updateFilterKeyword = (ev, filterKey) => {
        if (!ev || !ev.target) {
            console.error("Evento no definido:", ev);
            return;
        }
        this.state.filtersKeywords[filterKey] = ev.target.value;
        this.applyFiltersKeyword();
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

    exportToExcelKeywords() {
        if (this.state.filteredKeywords.length === 0) {
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

        let filteredData = this.state.filteredKeywords.map(record => {
            let newRecord = {};
            Object.keys(columnMap).forEach(key => {
                newRecord[columnMap[key]] = record[key];
            });
            return newRecord;
        });

        let worksheet = XLSX.utils.json_to_sheet(filteredData);

        let workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, "Keywords");

        XLSX.writeFile(workbook, "Keywords.xlsx");
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

registry.category("actions").add("vex_sync_mercado_libre.brand_ads", BrandADS);


