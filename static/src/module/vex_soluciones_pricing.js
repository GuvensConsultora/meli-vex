/** @odoo-module **/

import { Component, useState, useEffect, useRef, onWillUnmount, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { jsonrpc } from "@web/core/network/rpc_service";
import { loadBundle, loadJS } from "@web/core/assets";
let current_user = 'User';


class ChatbotTemplate extends Component {
  static template = "vex_sync_mercado_libre.pricing";

  setup() {
    this.chartLibReady = useRef(false);
    this.dataReady = useRef(false);
    //Code to open view
    this.rpc = useService("rpc");  // Using the RPC service
    this.action = useService("action");  // Using the Action service to open the view
    const today = new Date();
    const currentMonth = today.toISOString().slice(0, 7);
    self = this.action; // Ensure self is set in the constructor

    this.http = useService("http");
    this.orm = useService("orm");
    this.dialog = useService("dialog");
    this.notificationService = useService("notification");

   //const ajax = require('web.ajax');
    console.log('Component setup executed');
    this.state = useState({
      price_score: '',
      total_sales: 0,
      last_month_sales: 0,
      increased_profit: 0,
      profit_margin: 0,
      below_avg_price: 0,
      in_avg_price: 0,
      above_avg_price: 0,
      currency_symbol: '',
      new_customers_last_month:0,
      total_customers_count: 0,
      products_count: 0,
      questions_count : 0,
      competitors_count: 0,
      selectedMenuOption: "dashboard",
      isLeftSidebarVisible: true,
      isRightSidebarVisible: false,
      isCentralSidebarVisible: false,
      isEditSidebarVisible: false,
      isChatGPTConfigActive: false,
      isChecked: false,
      selectedMonth: currentMonth,
      showModal: false,

      profit_evolution :{},
      daily_sales_evol :{},
      price_evolution_grouped :{},
      products_prices :[],
      items: [],
      data: [],
    });
    console.log('Calling loadData...');

    this.canvasRef = useRef("productosSincronizadosChart");
    this.canvasRef2 = useRef("averagePriceChart");
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
        await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js");
        this.chartLibReady.value = true;

        await this.load_data(); // espera a que cargue la data
        
        this.dataReady.value = true;
    });
    
    onMounted(async () => {
      const instances = await this.orm.searchRead("vex.instance", [
          ["license_valid_str", "=", "active"],
          ["store_type", "=", "mercadolibre"],
      ], ["id"]);
      if (instances.length === 0) {
          this.state.showModal = true;
      } else {
          this.state.showModal = false;
      }
    });

    useEffect(() => {
        if (!this.chartLibReady.value || !this.dataReady.value) return;

        const grid = GridStack.init({
            cellHeight: 'auto',
            animate: false,
        }).on('change', (ev, gsItems) => {
            this.column = grid.getColumn();
            console.log(this.column);
        });

        this.renderChart();
        this.renderChart2();
        this.renderChart3();
        this.renderChart4();
        this.renderChart6();
        this.renderChart7();

    }, () => [this.chartLibReady.value, this.dataReady.value]);


    onWillUnmount(() => {
        this.onWillUnmount()
        this.delBackground()
    });
    //this.load_data();
    //this.getSessionInfo();
  }
  
  redirigirAConfiguracion() {
    this.action.doAction("vex_sync_store.vex_sync_store_open_instances");
  }

  get salesGrowthText() {
    console.log("Evaluando salesGrowthText con", this.state.total_sales, this.state.last_month_sales);
    const total = this.state.total_sales;
    const last = this.state.last_month_sales;

    if (!total || !last) {
        return {
            text: '⬆0% since last month',
            class: 'text-success'
        };
    }

    const growth = ((total - last) / last) * 100;
    const growthFixed = Math.abs(growth).toFixed(2);

    if (growth >= 0) {
        return {
            text: `⬆${growthFixed}% since last month`,
            class: 'text-success'
        };
    } else {
        return {
            text: `⬇${growthFixed}% since last month`,
            class: 'text-danger'
        };
    }
    }

  async load_data(){
  //   this.fetchOrdersSyncedToday();
    await this.fetchPriceScoreLetter();
    await this.fetchTotalSales();
    await this.fetchLastMonthSales();
    await this.fetchProductPrices();
    await this.fetchAvgProfitMargin();
    await this.fetchBelowAvgPrice();
    await this.fetchInAvgPrice();
    await this.fetchAboveAvgPrice();
    await this.fetchProfitMarginEvolution();
    await this.fetchPriceEvolutionGrouped();
    await this.fetchDailySalesEvolution();
    await this.fetchProfitGrowth();
    await this.fetchTotalCompetitorsCount();
    await this.fetchTotalProductsCount();

    this.render();
}

async fetchPriceScoreLetter (){
    try {
        let number = await jsonrpc('/web/dataset/call_kw', {
            model: 'mercado.libre.product',
            method: 'get_score_letter',
            args: [],
            kwargs: {},
        });
        console.log("fetchPriceScoreLetter", number);
        this.state.price_score = number;
    } catch (e) {
        console.error("Error al obtener score letter:", e);
    }
  }

async fetchTotalSales (){
  let result = await jsonrpc('/web/dataset/call_kw', {
      model: 'sale.order',
      method: 'total_ventas_mercadolibre',
      args: [],
      kwargs: {}
  });
  console.log("fetchTotalSales",result) ;
  this.state.total_sales = result.total_sales;
  this.state.currency_symbol = result.currency_symbol;
  
}

async fetchLastMonthSales (){
    let result = await jsonrpc('/web/dataset/call_kw', {
        model: 'sale.order',
        method: 'mes_pasado_ventas_mercadolibre',
        args: [],
        kwargs: {}
    });
    console.log("fetchLastMonthSales",result) ;
    this.state.last_month_sales = result.total_sales;
  }

async fetchProductPrices (){
    let datos = await jsonrpc('/web/dataset/call_kw', {
        model: 'mercado.libre.product',
        method: 'get_all_products_with_avg_compared',
        args: [],
        kwargs: {}
    });
    
    console.log("ProductsData",datos) ;
    this.state.products_prices = datos;                       
}

async fetchAvgProfitMargin (){
    let datos = await jsonrpc('/web/dataset/call_kw', {
        model: 'mercado.libre.product',
        method: 'get_average_profit_margin',
        args: [],
        kwargs: {}
    });
    
    console.log("AvgProfitMargin",datos) ;
    this.state.profit_margin = datos;                       
}

async fetchBelowAvgPrice (){
    let datos = await jsonrpc('/web/dataset/call_kw', {
        model: 'mercado.libre.product',
        method: 'get_percentage_below_average',
        args: [],
        kwargs: {}
    });
    
    console.log("fetchBelowAvgPrice",datos) ;
    this.state.below_avg_price = datos;                       
}

async fetchInAvgPrice (){
    let datos = await jsonrpc('/web/dataset/call_kw', {
        model: 'mercado.libre.product',
        method: 'get_percentage_in_average',
        args: [],
        kwargs: {}
    });
    
    console.log("fetchInAvgPrice",datos) ;
    this.state.in_avg_price = datos;                       
}

async fetchAboveAvgPrice (){
    let datos = await jsonrpc('/web/dataset/call_kw', {
        model: 'mercado.libre.product',
        method: 'get_percentage_above_average',
        args: [],
        kwargs: {}
    });
    
    console.log("fetchAboveAvgPrice",datos) ;
    this.state.above_avg_price = datos;                       
}

async fetchProfitMarginEvolution (){
    let datos = await jsonrpc('/web/dataset/call_kw', {
        model: 'mercado.libre.product',
        method: 'get_profit_margin_evolution',
        args: [],
        kwargs: {}
    });
    
    console.log("fetchProfitMarginEvolution",datos) ;
    this.state.profit_evolution = datos;                       
}

async fetchPriceEvolutionGrouped (){
    let datos = await jsonrpc('/web/dataset/call_kw', {
        model: 'mercado.libre.product',
        method: 'get_price_evolution_grouped',
        args: [],
        kwargs: {}
    });
    
    console.log("fetchPriceEvolutionGrouped",datos) ;
    this.state.price_evolution_grouped = datos;                       
}

async fetchDailySalesEvolution (){
    let datos = await jsonrpc('/web/dataset/call_kw', {
        model: 'mercado.libre.product',
        method: 'get_daily_sales_evolution',
        args: [],
        kwargs: {}
    });
    
    console.log("fetchDailySalesEvolution",datos) ;
    this.state.daily_sales_evol = datos;                       
}

async fetchProfitGrowth (){
    let datos = await jsonrpc('/web/dataset/call_kw', {
        model: 'mercado.libre.product',
        method: 'get_monthly_profit_growth',
        args: [],
        kwargs: {}
    });
    
    console.log("fetchProfitGrowth",datos) ;
    this.state.increased_profit = datos;                       
}

async total_orders_views(){
  this.notificationService.add("Abriendo vista ordenes", { type: 'warning' });

  try {
      this.rpc("/web/action/load", { action_id: "sale.action_orders" })
      .then((result) => {  
          const treeView = result.views.find((v) => v[1] === "list");
          console.log(result);
          this.action.doAction({
              name: 'Sales Orders',
              type: 'ir.actions.act_window',
              res_model: 'sale.order',
              target: 'current',
              domain: [],
              views: [[treeView[0], 'tree']],
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

async fetchTotalProductsCount (){
  let number = await jsonrpc('/web/dataset/call_kw', {
      model: 'mercado.libre.product',
      method: 'get_total_products',
      args: [],
      kwargs: {}
  });
  this.state.products_count = number;        
}

async fetchTotalCompetitorsCount (){
  let number = await jsonrpc('/web/dataset/call_kw', {
      model: 'mercado.libre.product.compared',
      method: 'get_total_competitors',
      args: [],
      kwargs: {}
  });
  this.state.competitors_count = number;        
}

  onMessage({ detail: notifications }) {
    console.log("ACTUALIZACION")
         }
 
  selectMenuOption(option) {

    this.state.selectedMenuOption = option;
    if (option === 'history') {
        // Si es 'history', ejecutar la función que quieres correr de nuevo
        //this.loadhistory();
    }
    if (option === 'pending') {
      // Si es 'history', ejecutar la función que quieres correr de nuevo
    //  this.loadData();
  }

  }

 
  toggleSidebar(side) {
    
    switch (side) {
      case "left":
        this.state.isLeftSidebarVisible = !this.state.isLeftSidebarVisible;
        break;
      case "right":
        this.state.isRightSidebarVisible = !this.state.isRightSidebarVisible;
        break;
      case "central":
        this.state.isCentralSidebarVisible = !this.state.isCentralSidebarVisible;
        break;
      case "edit":
        this.state.isEditSidebarVisible = !this.state.isEditSidebarVisible;
        break;
    
      default:
        break;
    }
  }




  toggleRuleSidebar() {
    this.state.isRuleSidebarVisible = !this.state.isRuleSidebarVisible;
    
}



  

async deleteRule(ev) {
  const itemId = ev.target.id; 
  
  // Aquí puedes agregar la lógica para eliminar la regla
  let updateRule = await jsonrpc('/web/dataset/call_kw', {
    model: 'vex.auto.response',
    method: 'deleteRule',
    args: [],  
    kwargs: {
      record_id: itemId
    }
  });

  console.log('Eliminar regla con id:', itemId,updateRule);

}

async open_export_view() {
    try {
      this.action.doAction({
        name: 'Customers',
        type: 'ir.actions.act_window',
        res_model: "mercado.libre.product",
        target: 'current',
        domain: [], // Specify your domain if needed
        views: [[false, 'form']], // Use the form view for the order list
      });
  
      const response = await this.rpc("/web/action/load", { action_id: "sale.action_orders" });
    } catch (error) {
      console.error("Error opening the Sale Orders view:", error);
    }
  }


async open_pricing_rules_view() {
    try {
      this.action.doAction({
        name: 'Reglas de Precios',
        type: 'ir.actions.act_window',
        res_model: 'mercado.libre.product',
        target: 'current',
        domain: [["data_type", "=", "master"]],
        views: [[false, 'tree'], [false, 'form']], // Use the tree and form views for the pricing rules
      });
    } catch (error) {
      console.error("Error opening the Pricing Rules view:", error);
    }
  }
  

 async editeRule(ev) {
  const itemId = ev.target.id; 
  
  // Aquí puedes agregar la lógica para eliminar la regla
  let rule_data = await jsonrpc('/web/dataset/call_kw', {
    model: 'vex.auto.response',
    method: 'get_rule_by_id',
    args: [],  
    kwargs: {
      response_id: itemId
    }
  });

  console.log('Datos', itemId,rule_data);
  this.toggleSidebar('edit');

  const NewanswerText = document.querySelector("#answerText_edit");
  const NewautoResponse = document.querySelector("#autoResponse_edit");
  const NewruleType = document.querySelector("#ruleType_edit");
  const edit_button = document.querySelector("#button_edit");

  NewanswerText.value = rule_data.userInput;
  NewautoResponse.value = rule_data.autoResponse;
  NewruleType.value = rule_data.ruleType;

  //edit_button.id = itemId;
  edit_button.setAttribute("rule-to-edit-id", itemId);


}

async udpateRuleData(event){
  const NewanswerText = document.querySelector("#answerText_edit").value;
  const NewautoResponse = document.querySelector("#autoResponse_edit").value;
  const NewruleType = document.querySelector("#ruleType_edit").value;
  
  const Id = event.target.id; 
  const edit_button = document.querySelector(`#${Id}`);
  
  const id_rule = edit_button.getAttribute("rule-to-edit-id");
  

  //console.log(NewanswerText,NewautoResponse,NewruleType, Id);
  

  let rule_data = await jsonrpc('/web/dataset/call_kw', {
    model: 'vex.auto.response',
    method: 'update_rule',
    args: [],  
    kwargs: {
      response_id: id_rule,
      isRuleActive: false,
      userInput: NewanswerText,
      autoAnswer: NewautoResponse,
      ruleType: NewruleType

    }
  });

  console.log(rule_data);

  this.toggleSidebar('edit')



  
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
  let percentageAtMarketAverage = this.state.in_avg_price;
  let remaining = 100 - percentageAtMarketAverage; // Parte vacía

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

  let percentageBelowAverage = this.state.below_avg_price; // % de productos por debajo del promedio
  let remaining = 100 - percentageBelowAverage; // Parte vacía del gauge

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
  let months = this.state.price_evolution_grouped.months//['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  let ourPrices = this.state.price_evolution_grouped.ourPrices//months.map(() => Math.floor(80 + Math.random() * 20)); // Precios entre $80 y $100
  let competitorPrices = this.state.price_evolution_grouped.competitorPrices//ourPrices.map(price => price + Math.floor(Math.random() * 10 - 5)); // Variación en la competencia

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
  let percentageAboveCompetitorPrice = this.state.above_avg_price;
  let remaining = 100 - percentageAboveCompetitorPrice; // Parte vacía

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
  let days = this.state.daily_sales_evol.days;

  // Datos estáticos con tendencia ascendente y algunas caídas
  let salesData = this.state.daily_sales_evol.sales;

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
  const months = this.state.profit_evolution.months;

  // Datos estáticos con una ligera tendencia alcista y retrocesos
  const profitMargins = this.state.profit_evolution.profitMargins; 

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


delBackground() {
  const actionManagerEl = document.querySelector('.o_action_manager');
  if (actionManagerEl.id = 'doodles') {
      actionManagerEl.id = null;
      actionManagerEl.classList.remove('list-contact');
  } else {
      console.warn('Elemento .o_action_manager no encontrado.');
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



}

registry.category("actions").add("vex_sync_mercado_libre.pricing", ChatbotTemplate);
