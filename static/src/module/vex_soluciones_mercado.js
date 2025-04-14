/** @odoo-module **/

import { loadBundle, loadJS } from "@web/core/assets";
import { Component, onWillUnmount, useEffect, useRef, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { jsonrpc } from "@web/core/network/rpc_service";
//import Chart from "chart.js/auto";




class MercadoTemplate extends Component {
    static template = "vex_sync_mercado_libre.mercado";

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
            description: "",
            segments: [],
            orders_number: 200,
            total_orders: 100,
            new_customers_last_month: 0,
            total_customers_count: 0,
            products_count: 0,
            questions_count : 0,
            top_clients_data :[],
            top_products_data : [],
            latest_orders :[],
            chart_customers_evolution : [],
            monthly_profit_last_6_months : [],
            average_custom_order :[],
            top_5_categories_data :[],
            CompletedAndCanceled4months_data : [],
            get_sales_by_channel_last_5_months_data : [],
            question_count_by_category_data : [],

            text : "siuu",
            selectedSegment: null,
            column: "",
            items: [
                // { w: 2, h: 2, content: 'my first widget' }, 
                // { w: 2, content: 'another longer widget!' } 
            ]

        });
        
        this.canvasRef = useRef("productosSincronizadosChart");
        this.canvasRef2 = useRef("categoriasProductosChart");
        this.canvasRef3 = useRef("pie1");
        this.canvasRef4 = useRef("line1");
        this.canvasRef5 = useRef("bar1");
        this.canvasRef6 = useRef("radar1");
        this.canvasRef7 = useRef("doughnut1");
        //this.canvasRef8 = useRef("polarArea1");
        //this.canvasRef9 = useRef("bubble1");
        this.chart = null;
        this.chart2 = null;
        this.chart3 = null;
        this.chart4 = null;
        //this.chart5 = null;
        this.chart6 = null;
        this.chart7 = null;
        //this.chart8 = null;
        //this.chart9 = null;
               

        onWillStart(async () => {           
            await loadBundle("web.chartjs_lib");
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js")
        });

        // Inicializar los "segmentos" (partners) al montar el componente
        onWillStart(async () => {            
            
            this.addBackground()
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

            this.renderChart();
            this.renderChart2();
            this.renderChart3();
            this.renderChart4();
            this.renderChart6();
            this.renderChart7();

            grid.load(this.state.items);

            this.load_data();

        },() => []    
            );


        onWillUnmount(() => {
            this.onWillUnmount()
            this.delBackground()
        });

        //this.load_data();
    }


    // Load dashboard data

     async load_data(){
        this.fetchOrdersSyncedToday();
        this.fetchTotalOrders();
        this.fetchNewCustomersLastMonth();
        this.fetchTotalCustomersCount();
        this.fetchTotalProductsCount();
        this.fectNewCustomerLastSixMonths();
        this.fetchMonthlyProfitLastSixMonths();
        this.fetchTopClients();
        this.fetchTopProducts();
        this.fetchLatestOrders();
        //this.get_average_custom_order_last_6_months();
        this.top_5_categories();
       // this.CompletedAndCanceled4months();
        this.get_sales_by_channel_last_5_months();
        this.get_questions_count();
        //this.question_count_by_category();



        this.render();

        
    }

    async fetchOrdersSyncedToday(){
        let number = await jsonrpc('/web/dataset/call_kw', {
            model: 'sale.order',
            method: 'orders_synced_today',
            args: [],
            kwargs: {}
        });
        this.state.orders_number = number;
    }

    async fetchTotalOrders (){
        let number = await jsonrpc('/web/dataset/call_kw', {
            model: 'sale.order',
            method: 'get_total_orders_count',
            args: [],
            kwargs: {}
        });
        this.state.total_orders = number;
    }

    async fetchNewCustomersLastMonth (){
        let number = await jsonrpc('/web/dataset/call_kw', {
            model: 'sale.order',
            method: 'get_new_customers_first_purchase_this_month',
            args: [],
            kwargs: {}
        });
        this.state.new_customers_last_month = number;
        
    }

    async fetchTotalCustomersCount (){
        let number = await jsonrpc('/web/dataset/call_kw', {
            model: 'sale.order',
            method: 'count_customers_with_server_meli',
            args: [],
            kwargs: {}
        });
        this.state.total_customers_count = number;        
    }

    async fetchTotalProductsCount (){
        let number = await jsonrpc('/web/dataset/call_kw', {
            model: 'sale.order',
            method: 'get_total_products',
            args: [],
            kwargs: {}
        });
        this.state.products_count = number;        
    }

    async fectNewCustomerLastSixMonths (){
        let datos = await jsonrpc('/web/dataset/call_kw', {
            model: 'sale.order',
            method: 'get_or_update_new_customers_data',
            args: [],
            kwargs: {}
        });
        this.state.chart_customers_evolution = datos;   
        // Extraer etiquetas (meses) y datos (nuevos clientes) para el gráfico
        console.log("Los datos",datos) ;
        this.renderChart();
        this.chart.update();
    


    }

    async fetchMonthlyProfitLastSixMonths (){
        let datos = await jsonrpc('/web/dataset/call_kw', {
            model: 'sale.order',
            method: 'get_monthly_profit_last_6_months',
            args: [],
            kwargs: {}
        });

        this.state.monthly_profit_last_6_months = datos;  
        console.log("DATOS",datos) ;
        this.renderChart4();
        this.chart4.update();

    }
    

    async fetchTopClients (){
        let datos = await jsonrpc('/web/dataset/call_kw', {
            model: 'sale.order',
            method: 'get_top_clients_all_time',
            args: [],
            kwargs: {}
        });
        
        console.log("Topclients",datos) ;
        this.state.top_clients_data = datos;                       
    }

    async fetchTopProducts (){
        let datos = await jsonrpc('/web/dataset/call_kw', {
            model: 'sale.order',
            method: 'get_top_products_all_time',
            args: [],
            kwargs: {}
        });
        

        if (typeof datos === "string") {
            console.log("Es una cadena:", datos);
        } else if (Array.isArray(datos)) {
            console.log("Es un array:", datos);
        } else {
            console.log("No es ni una cadena ni un array.");
        }

        
        console.log("TopProducts",datos) ;        
        this.state.top_products_data = datos;


    }

    async fetchLatestOrders (){
        let datos = await jsonrpc('/web/dataset/call_kw', {
            model: 'sale.order',
            method: 'get_latest_orders',
            args: [],
            kwargs: {}
        });
        
        console.log("Latest Orders",datos) ;
        this.state.latest_orders = datos;                       
    }

   

    async top_5_categories(){
        console.log("top_categories") ;
        
        let datos = await jsonrpc('/web/dataset/call_kw', {
            model: 'sale.order',
            method: 'get_top_categories',
            args: [],
            kwargs: {}
        });
        
        console.log("top_categories",datos) ;
        this.state.top_5_categories_data = datos; 
        

        this.renderChart3();
        this.chart3.update();
        
    }

    




    

    async get_sales_by_channel_last_5_months(){

        console.log("get_sales_by_channel_last_5_months") ;
        
        let datos = await jsonrpc('/web/dataset/call_kw', {
            model: 'sale.order',
            method: 'get_sales_by_channel_last_5_months',
            args: [],
            kwargs: {}
        });
        
        console.log("get_sales_by_channel_last_5_months",datos) ;
        this.state.CompletedAndCanceled4months_data = datos;
        
        

        this.renderChart2();
        this.chart2.update();
        
    }

    async get_questions_count(){

        let datos = await jsonrpc('/web/dataset/call_kw', {
            model: 'vex.meli.questions',
            method: 'get_question_count',
            args: [],
            kwargs: {}
        });
        
        console.log("get_question_count",datos) ;
        this.state.questions_count = datos;

    }


    

   


    // Other code

    async total_orders_views(){
        this.notificationService.add("Abriendo vista productos", { type: 'warning' });

        // Code
        try {
            // Fetch the action related to the Sale Order
            

            this.rpc("/web/action/load", { action_id: "sale.action_orders" })
            .then((result) => {  // Change to arrow function to preserve 'this'
                const treeView = result.views.find((v) => v[1] === "list");
                console.log(result);
                // Open view with owl action service
                this.action.doAction({
                    name: 'Sales Orders',
                    type: 'ir.actions.act_window',
                    res_model: 'sale.order',
                    target: 'current',
                    domain: [], // Specify your domain if needed
                    views: [[treeView[0], 'tree']], // Use the tree view for the order list
                });
            })
            .catch((error) => {
                console.log(error);
                throw error;
            });
            
        } catch (error) {
            console.error("Error opening the Sale Orders view:", error);
        }

    }

    async customers_view(){
        this.notificationService.add("Abriendo vista customers", { type: 'warning' });

        // Code
        try {
            // Fetch the action related to the Sale Order
            

            this.rpc("/web/action/load", { action_id: "sale.action_orders" })
            .then((result) => {  // Change to arrow function to preserve 'this'
                const treeView = result.views.find((v) => v[1] === "list");
                console.log(result);
                // Open view with owl action service
                this.action.doAction({
                    name: 'Customers',
                    type: 'ir.actions.act_window',
                    res_model: 'res.partner',
                    target: 'current',
                    domain: [], // Specify your domain if needed
                    views: [[false, 'list']], // Use the tree view for the order list
                });
            })
            .catch((error) => {
                console.log(error);
                throw error;
            });
            
        } catch (error) {
            console.error("Error opening the Sale Orders view:", error);
        }

    }



    async open_client_view(){
        this.notificationService.add("Abriendo vista client", { type: 'warning' });

        // Code
        try {
            // Fetch the action related to the Sale Order
            

            this.rpc("/web/action/load", { action_id: "sale.action_orders" })
            .then((result) => {  // Change to arrow function to preserve 'this'
                const treeView = result.views.find((v) => v[1] === "list");
                console.log(result);
                // Open view with owl action service
                this.action.doAction({
                    name: 'Client',
                    type: 'ir.actions.act_window',
                    res_model: 'res.partner',
                    res_id: 888,
                    target: 'new',
                    domain: [], // Specify your domain if needed
                    views: [[false, 'form']], // Use the tree view for the order list
                });
            })
            .catch((error) => {
                console.log(error);
                throw error;
            });
            
        } catch (error) {
            console.error("Error opening the Sale Orders view:", error);
        }

    }

    async open_order_view(){
        this.notificationService.add("Abriendo vista client", { type: 'warning' });

        // Code
        try {
            // Fetch the action related to the Sale Order
            

            this.rpc("/web/action/load", { action_id: "sale.action_orders" })
            .then((result) => {  // Change to arrow function to preserve 'this'
                const treeView = result.views.find((v) => v[1] === "list");
                console.log(result);
                // Open view with owl action service
                this.action.doAction({
                    name: 'Order',
                    type: 'ir.actions.act_window',
                    res_model: 'sale.order',
                    res_id: 888,
                    target: 'new',
                    domain: [], // Specify your domain if needed
                    views: [[false, 'form']], // Use the tree view for the order list
                });
            })
            .catch((error) => {
                console.log(error);
                throw error;
            });
            
        } catch (error) {
            console.error("Error opening the Sale Orders view:", error);
        }

    }

    async open_product_view(){
        this.notificationService.add("Abriendo vista client", { type: 'warning' });

        // Code
        try {
            // Fetch the action related to the Sale Order
            

            this.rpc("/web/action/load", { action_id: "sale.action_orders" })
            .then((result) => {  // Change to arrow function to preserve 'this'
                const treeView = result.views.find((v) => v[1] === "list");
                console.log(result);
                // Open view with owl action service
                this.action.doAction({
                    name: 'Product',
                    type: 'ir.actions.act_window',
                    res_model: 'product.template',
                    res_id: 888,
                    target: 'new',
                    domain: [], // Specify your domain if needed
                    views: [[false, 'form']], // Use the tree view for the order list
                });
            })
            .catch((error) => {
                console.log(error);
                throw error;
            });
            
        } catch (error) {
            console.error("Error opening the Sale Orders view:", error);
        }

    }

    async products_view(){
        this.notificationService.add("Abriendo vista productos", { type: 'warning' });

        // Code
        try {
            // Fetch the action related to the Sale Order
            

            this.rpc("/web/action/load", { action_id: "sale.action_orders" })
            .then((result) => {  // Change to arrow function to preserve 'this'
                const treeView = result.views.find((v) => v[1] === "list");
                console.log(result);
                // Open view with owl action service
                this.action.doAction({
                    name: 'Products',
                    type: 'ir.actions.act_window',
                    res_model: 'product.template',
                    target: 'current',
                    domain: [], // Specify your domain if needed
                    views: [[false, 'kanban']],// Use the tree view for the order list
                });
            })
            .catch((error) => {
                console.log(error);
                throw error;
            });
            
        } catch (error) {
            console.error("Error opening the Sale Orders view:", error);
        }

    }

    async questions_view(){
        this.notificationService.add("Abriendo vista productos", { type: 'warning' });

        // Code
        try {
            // Fetch the action related to the Sale Order
            

            this.rpc("/web/action/load", { action_id: "sale.action_orders" })
            .then((result) => {  // Change to arrow function to preserve 'this'
                const treeView = result.views.find((v) => v[1] === "list");
                console.log(result);
                // Open view with owl action service
                this.action.do_action({
                    name: 'Questions',
                    type: 'ir.actions.act_window',
                    res_model: 'vex.meli.questions',  // Your custom model
                    target: 'current',                // Open in the current window
                    views: [[false, 'tree'], [false, 'form']],  // Use tree or form view
                    domain: [],  // Optional: you can define a filter here if needed
                });
            })
            .catch((error) => {
                console.log(error);
                throw error;
            });
            
        } catch (error) {
            console.error("Error opening the Sale Orders view:", error);
        }

    }


    addBackground() {
        const actionManagerEl = document.querySelector('.o_action_manager');
        if (actionManagerEl) {
            actionManagerEl.id = 'doodles';
            actionManagerEl.classList.add('list-contact');
        } else {
            console.warn('Elemento .o_action_manager no encontrado.');
        }
    }

    delBackground() {
        const actionManagerEl = document.querySelector('.o_action_manager');
        if (actionManagerEl.id = 'doodles') {
            actionManagerEl.id = null;
            actionManagerEl.classList.remove('list-contact');
        } else {
            console.warn('Elemento .o_action_manager no encontrado.');
        }
    }
        
    

    selectSegment(ev) {
        this.state.selectedSegment = this.state.segments.find(segment => segment.id == ev.target.value);
        console.log(this.state);
    }

    renderChart() {
        if (this.chart) {
            this.chart.destroy();
        }
    
        // Datos de ejemplo: 20% de productos están en el precio promedio del mercado
        const percentageAtMarketAverage = 20;
        const remaining = 100 - percentageAtMarketAverage; // Parte vacía
    
        this.chart = new Chart(this.canvasRef.el, {
            type: "doughnut",
            data: {
                datasets: [{
                    data: [percentageAtMarketAverage, remaining], // Datos para el gauge
                    backgroundColor: ['rgba(54, 162, 235, 0.8)', 'rgba(200, 200, 200, 0.2)'], // Azul y gris
                    borderWidth: 0 // Sin bordes
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%', // Grosor del anillo
                circumference: 180, // Hace que sea un semicírculo
                rotation: 270, // Rota para empezar desde abajo
                plugins: {
                    title: {
                        display: true,
                        text: `Products at Market Average Price: ${percentageAtMarketAverage}%`,
                        font: {
                            size: 20
                        }
                    },
                    legend: {
                        display: false // Ocultamos la leyenda
                    },
                    tooltip: {
                        enabled: false // Desactiva tooltips
                    }
                }
            }
        });
    }
    


    renderChart2() {
        if (this.chart2) {
            this.chart2.destroy();
        }
    
        // Datos de ejemplo (puedes cambiarlos dinámicamente)
        const percentageBelowAverage = 40; // % de productos por debajo del promedio
        const remaining = 100 - percentageBelowAverage; // Parte vacía del gauge
    
        this.chart2 = new Chart(this.canvasRef2.el, {
            type: "doughnut",
            data: {
                datasets: [{
                    data: [percentageBelowAverage, remaining], // Solo dos valores: el porcentaje y el espacio vacío
                    backgroundColor: ['rgba(54, 162, 235, 0.8)', 'rgba(200, 200, 200, 0.2)'], // Azul y gris
                    borderWidth: 0 // Elimina bordes
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%', // Ajusta el grosor del anillo
                circumference: 180, // Hace que el gráfico sea un semi-círculo
                rotation: 270, // Rota el gráfico para que empiece desde abajo
                plugins: {
                    title: {
                        display: true,
                        text: `Below Average Price: ${percentageBelowAverage}%`,
                        font: {
                            size: 20
                        }
                    },
                    legend: {
                        display: false // Ocultamos la leyenda ya que no es necesaria en un gauge
                    },
                    tooltip: {
                        enabled: false // Desactiva tooltips para evitar confusión
                    }
                }
            }
        });
    }
    

    renderChart3() {
        if (this.chart3) {
            this.chart3.destroy();
        }
    
        // Datos de prueba para 12 meses
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const ourPrices = months.map(() => Math.floor(80 + Math.random() * 20)); // Precios entre $80 y $100
        const competitorPrices = ourPrices.map(price => price + Math.floor(Math.random() * 10 - 5)); // Variación en la competencia
    
        this.chart3 = new Chart(this.canvasRef3.el, {
            type: "line",
            data: {
                labels: months,
                datasets: [
                    {
                        label: 'Our Prices ($)',
                        data: ourPrices,
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true
                    },
                    {
                        label: 'Competitor Prices ($)',
                        data: competitorPrices,
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        borderWidth: 2,
                        borderDash: [5, 5], // Línea punteada para competencia
                        tension: 0.3,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Evolution of Competitiveness - Price Comparison',
                        font: {
                            size: 24
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(tooltipItem) {
                                let label = tooltipItem.dataset.label || '';
                                let value = tooltipItem.raw || 0;
                                return `${label}: $${value.toFixed(2)}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        grid: {
                            display: true,
                            color: "rgba(200, 200, 200, 0.2)"
                        },
                        title: {
                            display: true,
                            text: 'Price ($)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        title: {
                            display: true,
                            text: 'Months'
                        }
                    }
                }
            }
        });
    }
    

    renderChart4() {
        if (this.chart4) {
            this.chart4.destroy();
        }
    
        // Datos de ejemplo: 40% de productos están por encima del precio de la competencia
        const percentageAboveCompetitorPrice = 40;
        const remaining = 100 - percentageAboveCompetitorPrice; // Parte vacía
    
        this.chart4 = new Chart(this.canvasRef4.el, {
            type: "doughnut",
            data: {
                datasets: [{
                    data: [percentageAboveCompetitorPrice, remaining], // Datos para el gauge
                    backgroundColor: ['rgba(255, 159, 64, 0.8)', 'rgba(200, 200, 200, 0.2)'], // Naranja y gris
                    borderWidth: 0 // Sin bordes
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%', // Grosor del anillo
                circumference: 180, // Hace que sea un semicírculo
                rotation: 270, // Rota para empezar desde abajo
                plugins: {
                    title: {
                        display: true,
                        text: `Products Above Competitor Price: ${percentageAboveCompetitorPrice}%`,
                        font: {
                            size: 20
                        }
                    },
                    legend: {
                        display: false // Ocultamos la leyenda
                    },
                    tooltip: {
                        enabled: false // Desactiva tooltips
                    }
                }
            }
        });
    }
    
 
    

    renderChart6() {
        if (this.chart6) {
            this.chart6.destroy();
        }
    
        // Días del mes (30 días)
        const days = [
            "Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7", "Day 8", "Day 9", "Day 10",
            "Day 11", "Day 12", "Day 13", "Day 14", "Day 15", "Day 16", "Day 17", "Day 18", "Day 19", "Day 20",
            "Day 21", "Day 22", "Day 23", "Day 24", "Day 25", "Day 26", "Day 27", "Day 28", "Day 29", "Day 30"
        ];
    
        // Datos estáticos con tendencia ascendente y algunas caídas
        const salesData = [
            600, 620, 640, 660, 680, 670, 690, 710, 730, 750,
            770, 760, 780, 800, 820, 810, 830, 850, 870, 890,
            910, 900, 920, 940, 960, 950, 970, 990, 1010, 1030
        ];
    
        this.chart6 = new Chart(this.canvasRef6.el, {
            type: "line",
            data: {
                labels: days,
                datasets: [
                    {
                        label: 'Actual Sales',
                        data: salesData,
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Sales Evolution',
                        font: {
                            size: 24
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false,
                        grid: {
                            display: true,
                            color: "rgba(200, 200, 200, 0.2)"
                        },
                        title: {
                            display: true,
                            text: 'Units Sold'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        title: {
                            display: true,
                            text: 'Days'
                        }
                    }
                }
            }
        });
    }
    
    
    
    renderChart7() {
        if (this.chart7) {
            this.chart7.destroy();
        }
    
        // Meses del análisis
        const months = ['August', 'September', 'October', 'November', 'December', 'January'];
    
        // Datos estáticos con una ligera tendencia alcista y retrocesos
        const profitMargins = [22, 26, 24, 28, 30, 27]; 
    
        this.chart7 = new Chart(this.canvasRef7.el, {
            type: "line",
            data: {
                labels: months,
                datasets: [
                    {
                        label: 'Actual Profit Margin (%)',
                        data: profitMargins,
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Evolution of Profit Margin',
                        font: {
                            size: 24
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false,
                        grid: {
                            display: true,
                            color: "rgba(200, 200, 200, 0.2)"
                        },
                        title: {
                            display: true,
                            text: 'Profit Margin (%)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        title: {
                            display: true,
                            text: 'Months'
                        }
                    }
                }
            }
        });
    }
    
   

    
    onWillUnmount() {
        if (this.chart) {
            this.chart.destroy();
        }
        if (this.chart2) {
            this.chart2.destroy();
        }

        
    }

    async sendMassMessage() {
        if (!this.state.selectedSegment) {
            alert("Por favor, seleccione un segmento antes de enviar.");
            return;
        }

        const success = await this.orm.call(
            "res.partner.segment",
            "send_mass_message",
            // AQUÍ CAMBIAS AL MODELO DE SEGMENTOS DE ODOO ESTO ES SOLO PRUEBA
            [this.state.selectedSegment, this.state.title, this.state.description]
        );

        if (success) {
            alert("Mensaje enviado exitosamente.");
        } else {
            alert("Hubo un error al enviar el mensaje.");
        }

        this.toggleModal(false);
    }
}

registry.category("actions").add("vex_sync_mercado_libre.mercado", MercadoTemplate);


