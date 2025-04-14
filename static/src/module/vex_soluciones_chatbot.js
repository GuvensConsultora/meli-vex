/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

import { useBus } from "@web/core/utils/hooks";
import { jsonrpc } from "@web/core/network/rpc_service";
let current_user = 'User';



class ChatbotTemplate extends Component {
  static template = "vex_sync_mercado_libre.chatbot";

  setup() {


   //const ajax = require('web.ajax');
    console.log('Component setup executed');
    this.state = useState({
      selectedMenuOption: "pending",
      isLeftSidebarVisible: true,
      isRightSidebarVisible: false,
      isCentralSidebarVisible: false,
      isEditSidebarVisible: false,
      isChatGPTConfigActive: false,
      isChecked: false,
      items: [
          {
              ruleActive: true,
              userInput: '¿Cuánto cuesta el envío?',
              autoResponse: 'Fast answer',
              ruleType: 'Al inicio',
          },
          {
              ruleActive: false,
              userInput: '¿Cómo hacer un seguimiento?',
              autoResponse: 'Standard answer',
              ruleType: 'Al final',
          },
          {
              ruleActive: true,
              userInput: '¿Qué opciones de pago ofrecen?',
              autoResponse: 'We offer credit/debit cards, PayPal, and bank transfer.',
              ruleType: 'Durante la compra',
          },
          {
              ruleActive: true,
              userInput: '¿Puedo cancelar mi pedido?',
              autoResponse: 'Yes, you can cancel your order within 24 hours of placing it.',
              ruleType: 'Al inicio',
          },
          {
              ruleActive: false,
              userInput: '¿Cuándo recibiré mi reembolso?',
              autoResponse: 'Reimbursement is processed within 5-7 business days.',
              ruleType: 'Después del reembolso',
          },
          {
              ruleActive: true,
              userInput: '¿Este producto está en stock?',
              autoResponse: 'You can check stock availability on the product page.',
              ruleType: 'Durante la compra',
          },
          {
              ruleActive: true,
              userInput: '¿Ofrecen descuentos por volumen?',
              autoResponse: 'Yes, we offer bulk discounts. Please contact customer service for more details.',     
              ruleType: 'Al final',
          }
      ],
    
      data: [
        {
          "id": "1234213",
          "name": " ",
          "questions": [
            {
              "id": "q1",
              "text": "Question 1.1",
              "time": "hace 10 minutos"
            },
            {
              "id": "q2",
              "text": "Question 1.2",
              "time": "hace 20 minutos"
            }
          ]
        },
        {
          "id": "1234",
          "name": " ",
          "questions": [
            {
              "id": "q3",
              "text": "Question 2.1",
              "time": "hace 30 minutos"
            },
            {
              "id": "q4",
              "text": "Question 2.2",
              "time": "hace 40 minutos"
            }
          ]
        },
        {
          "id": "123423",
          "name": " ",
          "questions": [
            {
              "id": "q5",
              "text": "Question 3.1",
              "time": "hace 50 minutos"
            },
            {
              "id": "q6",
              "text": "Question 3.2",
              "time": "hace 60 minutos"
            }
          ]
        },
        {
          "id": "123412312",
          "name": " ",
          "questions": [
            {
              "id": "q7",
              "text": "Question 4.1",
              "time": "hace 70 minutos"
            },
            {
              "id": "q8",
              "text": "Question 4.2",
              "time": "hace 80 minutos"
            }
          ]
        }
      ],
      

    });
    console.log('Calling loadData...');
    this.loadData();
    this.getSessionInfo();
    this.loadRules();
  

  }


  onMessage({ detail: notifications }) {
    console.log("ACTUALIZACION")
         }
 
  selectMenuOption(option) {
    this.loadRules();

    this.state.selectedMenuOption = option;
    if (option === 'history') {
        // Si es 'history', ejecutar la función que quieres correr de nuevo
        this.loadhistory();
    }
    if (option === 'pending') {
      // Si es 'history', ejecutar la función que quieres correr de nuevo
      this.loadData();
  }

  }

  async getSessionInfo() {
    try {
        const session_info = await jsonrpc('/web/session/get_session_info', {});

        if (session_info) {
            current_user = session_info.name;
            console.log('Usuario actual:', current_user);
        }
    } catch (error) {
        console.error('Error al obtener la información de la sesión:', error);
    }
}


  async loadData() {
    try {
      // Obtener productos con meli_id válido
      let products = await jsonrpc('/web/dataset/call_kw', {
        model: 'product.template',
        method: 'search_read',
        args: [[], ['meli_code', 'name', 'thumbnail', 'list_price']],
        kwargs: {}
      });
      console.log(products);
  
      // Obtener todas las preguntas en una sola consulta, filtrando por meli_answer en el servidor
      let productIds = products.map(p => p.meli_code);
      let questions = await jsonrpc('/web/dataset/call_kw', {
        model: 'vex.meli.questions',
        method: 'search_read',
        args: [[['meli_item_id', 'in', productIds], ['meli_answer', '=', false]], ['meli_item_id', 'meli_text', 'meli_answer', 'meli_created_at', 'meli_id']],
        kwargs: {}
      });
      
      console.log(questions);
      // Formatear las fechas de creación de las preguntas
      questions = questions.map(question => {
        let meliCreatedAt = question.meli_created_at;
        let createdDate = new Date(meliCreatedAt);
        let currentDate = new Date();
        let differenceMs = currentDate - createdDate;
  
        // Convertir la diferencia a días, horas y minutos
        let differenceDays = Math.floor(differenceMs / (1000 * 60 * 60 * 24)); // Convertir a días
        let differenceHours = Math.floor((differenceMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)); // Horas restantes
        let differenceMinutes = Math.floor((differenceMs % (1000 * 60 * 60)) / (1000 * 60)).toString().padStart(2, '0'); // Minutos restantes
  
        // Crear el texto con el formato correcto
        let responseTimeText = '';
        if (differenceDays > 0) {
          responseTimeText += `${differenceDays}d `;
        }
        responseTimeText += `${differenceHours}hr ${differenceMinutes}min`;
        responseTimeText = responseTimeText.replace(/-/g, ' ');
  
        // Asignar el valor formateado
        question.meli_created_at = responseTimeText;
        return question;
      });

      console.log("Qustiosn" + questions);
  
      // Mapear preguntas a productos
      let productsWithQuestions = products.map(product => ({
        ...product,
        questions: questions.filter(q => q.meli_item_id === product.meli_code)
      })).filter(product => product.questions.length > 0);


      console.log(productsWithQuestions);
  
      // Actualizar el estado con los productos y preguntas
      this.state.data = productsWithQuestions;
  
      console.log('Data loaded:', this.state.data);
    } catch (error) {
      console.error('Error loading data:', error);
    }
  }

  async loadhistory(cargar_historia) {
    try {
      // Obtener productos con meli_id válido
      let products = await jsonrpc('/web/dataset/call_kw', {
        model: 'product.template',
        method: 'search_read',
        args: [[], ['meli_code', 'name', 'thumbnail', 'list_price']],
        kwargs: {},
      });
  
      // Obtener todas las preguntas filtradas por meli_id y meli_answer en una sola consulta
      let productIds = products.map(p => p.meli_code);
      let questions = await jsonrpc('/web/dataset/call_kw', {
        model: 'vex.meli.questions',
        method: 'search_read',
        args: [[['meli_item_id', 'in', productIds], ['meli_answer', '!=', false]], ['meli_item_id', 'meli_text', 'meli_answer', 'meli_created_at', 'meli_from_id', 'meli_id', 'meli_from_nickname', 'meli_answered_at', 'meli_answered_from_odoo', 'meli_odoo_answerer']],
        kwargs: {},
      });
  
      // Calcular el tiempo en el que se tardó en responder una pregunta
      questions = questions.map(question => {
        // Verificar si ambas propiedades existen antes de hacer cálculos
        if (question.meli_created_at && question.meli_answered_at) {
          let meliCreatedAt = question.meli_created_at;
          let createdDate = new Date(meliCreatedAt);
  
          let meliAnsweredAt = question.meli_answered_at;
          let currentDate = new Date(meliAnsweredAt);
  
          // Calcular la diferencia en milisegundos
          let differenceMs = currentDate - createdDate;
  
          // Convertir la diferencia a días, horas y minutos
          let differenceDays = Math.floor(differenceMs / (1000 * 60 * 60 * 24)); // Convertir a días
          let differenceHours = Math.floor((differenceMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)); // Horas restantes
          let differenceMinutes = Math.floor((differenceMs % (1000 * 60 * 60)) / (1000 * 60)).toString().padStart(2, '0'); // Minutos restantes
  
          // Crear el texto con el formato correcto
          let responseTimeText = '';
          if (differenceDays > 0) {
            responseTimeText += `${differenceDays}d `;
          }
          responseTimeText += `${differenceHours}hr ${differenceMinutes}min`;
          responseTimeText = responseTimeText.replace(/-/g, ' ');
  
          // Asignar el valor formateado a meli_answered_at
          question.meli_answered_at = responseTimeText;
        }
  
        // Determinar si fue respondida desde Odoo o Mercado Libre
        if (!question.meli_odoo_answerer) {
          question.meli_answered_from_odoo = "Mercado Libre";
        } else {
          question.meli_answered_from_odoo = "Odoo : " + question.meli_odoo_answerer;
        }
  
        return question;
      });
  
      // Mapear preguntas a productos
      let productsWithQuestions = products.map(product => ({
        ...product,
        questions: questions.filter(q => q.meli_item_id === product.meli_code)
      })).filter(product => product.questions.length > 0);
  
      // Actualizar el estado con los productos y preguntas
      this.state.data = productsWithQuestions;
  
      console.log('Data loaded:', this.state.data);
    } catch (error) {
      console.error('Error loading data:', error);
    }
  }

  toggleSidebar(side) {
    this.loadRules();
    
    switch (side) {
      case "left":
        this.state.isLeftSidebarVisible = !this.state.isLeftSidebarVisible;
        break;
      case "right":
        this.state.isRightSidebarVisible = !this.state.isRightSidebarVisible;
        this.loadGptConfig()
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



  toggleIsChatGPTConfigActive() {
    this.state.isChatGPTConfigActive = !this.state.isChatGPTConfigActive;
    this.UpdateGptBool(this.state.isChatGPTConfigActive);

  }

  async UpdateGptBool(bool_value) {
    try {
        // Realizar la llamada al servidor
        let updateRule = await jsonrpc('/web/dataset/call_kw', {
            model: 'vex.gpt.config',
            method: 'update_gpt_config',
            args: [],
            kwargs: {
                enable_gpt_responder: bool_value,             
            }
        });
        console.log("Estado sincronizado correctamente:", bool_value);
    } catch (error) {
        console.error("Error al sincronizar el estado:", error);
    }
}

 async botonResponder(itemId, element_id) {
    const responseText = document.getElementById('response-' + itemId).value;

    if (!responseText.trim()) {
        alert('No puedes enviar una respuesta vacía.');
        return;
    }

    console.log('Question ID:', itemId);
    console.log('Respuesta a enviar:', responseText);
    console.log('Item ID:', element_id);

    try {
        // Obtener el access token de Mercado Libre
        let instanceResult = await jsonrpc('/web/dataset/call_kw', {
            model: 'vex.instance',
            method: 'search_read',
            args: [],
            kwargs: {
                fields: ['access_token'], // Especifica el campo que deseas leer
            },
        });
        
        // Logging para verificar los datos retornados
        console.log('Datos retornados por search_read:', instanceResult);

       
        
        //let accessToken = instanceResult[0].access_token;
        let accessToken = 0;
        console.log(accessToken);

        // Enviar la respuesta a la pregunta llamando a la funcion de python
        let answerResult = await jsonrpc('/web/dataset/call_kw', {
            model: 'vex.import.wizard',
            method: 'answer_question',
            args: [itemId, responseText, accessToken],
            kwargs: {},
        });

        if (answerResult) {
            console.log('Respuesta enviada correctamente.');

            // Actualizar el campo `meli_answer` en `vex.meli.questions` con la respuesta
            let questions = await jsonrpc('/web/dataset/call_kw', {
                model: 'vex.meli.questions',
                method: 'search_read',
                args: [[['meli_id', '=', itemId]], ['id', 'meli_answer']], // Obtener el id para poder hacer el write
                kwargs: {},
            });

            if (questions.length > 0) {
                let questionId = questions[0].id; // Obtener el ID de la pregunta
                let currentDate = new Date();

                let formattedDate = currentDate.getFullYear() + '-' + 
                String(currentDate.getMonth() + 1).padStart(2, '0') + '-' + 
                String(currentDate.getDate()).padStart(2, '0') + ' ' + 
                String(currentDate.getHours()).padStart(2, '0') + ':' + 
                String(currentDate.getMinutes()).padStart(2, '0') + ':' + 
                String(currentDate.getSeconds()).padStart(2, '0');

                console.log(formattedDate);

                // Actualizar el valor de `meli_answer` en la base de datos
                await jsonrpc('/web/dataset/call_kw', {
                    model: 'vex.meli.questions',
                    method: 'write',
                    args: [[questionId], { 'meli_answer': responseText, 'meli_odoo_answerer': current_user, 'meli_answered_at': formattedDate , 'meli_status' : "ANSWERED"}],
                    kwargs: {},
                });

                console.log('El campo meli_answer ha sido actualizado correctamente.');
                this.loadData(); // Recargar los datos
                // Aquí puedes agregar cualquier lógica adicional para imprimir la respuesta si es necesario

            } else {
                console.error('No se encontró ninguna pregunta.');
            }
        } else {
            alert('Error al enviar la respuesta.');
        }
    } catch (error) {
        console.error('Error al procesar la solicitud:', error);
        alert('Hubo un error al procesar la solicitud.');
    }
}

async deleteButtonClick(questionid) {
  const confirmation = confirm('¿Estás seguro de borrar esto?');

  if (confirmation) {
      // Si el usuario hace clic en "Aceptar"
      console.log(`Borrar elemento con id: ${questionid}`);

      try {
          // Obtener el access token de Mercado Libre
          let instanceResult = await jsonrpc('/web/dataset/call_kw', {
              model: 'vex.instance',
              method: 'search_read',
              args: [],
              kwargs: {
                  fields: ['access_token'],
              },
          });

          let accessToken = instanceResult[0].access_token;
          console.log(accessToken);

          // Llamar al método para eliminar la pregunta en Mercado Libre
          let deleteResult = await jsonrpc('/web/dataset/call_kw', {
              model: 'vex.import.wizard',
              method: 'delete_question',
              args: [questionid, accessToken],
              kwargs: {},
          });

          if (deleteResult) {
              console.log('Respuesta eliminada correctamente de Mercado Libre');

              // Si la respuesta fue eliminada, buscar el ID de la pregunta en Odoo
              let questions = await jsonrpc('/web/dataset/call_kw', {
                  model: 'vex.meli.questions',
                  method: 'search_read',
                  args: [[['meli_id', '=', questionid]], ['id', 'meli_answer']], // Obtener el id para hacer el delete
                  kwargs: {},
              });

              if (questions.length > 0) {
                  let questionId = questions[0].id; // Obtener el ID de la pregunta

                  // Eliminar la pregunta de la base de datos
                  await jsonrpc('/web/dataset/call_kw', {
                      model: 'vex.meli.questions',
                      method: 'unlink',
                      args: [[questionId]],
                      kwargs: {},
                  });

                  console.log('La pregunta ha sido eliminada correctamente de la base de datos.');
                  this.loadData(); // Recargar los datos
              } else {
                  console.error('No se encontró ninguna pregunta.');
              }
          } else {
              alert('Error al eliminar la respuesta en Mercado Libre.');
          }
      } catch (error) {
          console.error('Error al procesar la solicitud:', error);
          alert('Hubo un error al procesar la solicitud.');
      }
  } else {
      // Si el usuario hace clic en "Cancelar"
      console.log('El usuario canceló la operación');
  }
}

// Automatic response  logic


async loadRules() {
  // Llamada JSON-RPC con los parámetros en kwargs
  let rules = await jsonrpc('/web/dataset/call_kw', {
      model: 'vex.auto.response',
      method: 'get_auto_responses',
      args: [],  
      kwargs: {}
  });
  this.state.items = rules;
  console.log("Rules",rules);
  
}

async loadGptConfig() {
  // Llamada JSON-RPC con los parámetros en kwargs
  let gpt_config = await jsonrpc('/web/dataset/call_kw', {
      model: 'vex.gpt.config',
      method: 'get_gpt_config',
      args: [],  
      kwargs: {}
  });
 

  this.state.isChatGPTConfigActive = gpt_config.enable_gpt_responder;
  //const gpt_key = document.querySelector("#openAIAPIKeyInp");
  const responseText = document.getElementById("openApiKey");
  responseText.value = gpt_config.chatgpt_key;
  const usage = document.getElementById("usageLimit");
  usage.value = gpt_config.daily_usage_limit;
  
  
  
}

async createNewRule(answerText, autoResponse, ruleType) {
  // Llamada JSON-RPC con los parámetros en kwargs
  let number = await jsonrpc('/web/dataset/call_kw', {
      model: 'vex.auto.response',
      method: 'create_auto_response_entry',
      args: [],  // Deja args vacío si estás usando kwargs
      kwargs: {
          user_input: answerText,     // Parametro esperado en Python
          auto_answer: autoResponse,       // Parametro esperado en Python
          rule_type: ruleType ,  // Valor predeterminado si no se especifica
          is_rule_active: false           // Puedes personalizar este valor
      }
  });
  console.log("respuesta", number);
  this.toggleSidebar('central');
  this.loadRules();
}

createRule() {
  // Captura los valores de los inputs
  const answerText = document.querySelector("#answerText").value;
  const autoResponse = document.querySelector("#autoResponse").value;
  
  const ruleType = document.querySelector("#ruleType").value;

  // Verifica que todos los campos estén llenos
  if (!answerText || !autoResponse || !ruleType) {
      alert("Todos los campos son obligatorios.");
      return; // Detiene la ejecución si falta algún campo
  }

  // Si todos los campos tienen valor, imprime los valores en la consola
  console.log({
      answerText,
      autoResponse,

      ruleType,
  });
  this.createNewRule(answerText,autoResponse,ruleType);
}

onCheckboxChange(event) {
  // Obtener el id del checkbox y su estado
  const checkboxId = event.target.id;  // El id del checkbox
  const isChecked = event.target.checked;  // Estado del checkbox (true o false)

  console.log('Checkbox ID:', checkboxId);  // Muestra el id del checkbox
  console.log('Checkbox Estado:', isChecked);  // Muestra el estado del checkbox

  // Aquí puedes realizar cualquier acción que necesites con el id y el estado
  // Ejemplo: actualizar el estado en tu modelo o enviar información al servidor
  this.updateRuleIsActive(checkboxId,isChecked);
}

async updateRuleIsActive(id,newStatus){
  let updateRule = await jsonrpc('/web/dataset/call_kw', {
    model: 'vex.auto.response',
    method: 'set_rule_active_status',
    args: [],  
    kwargs: {
      rule_id: id,     
      is_active: newStatus
    }
  });

  console.log(updateRule);

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
  this.loadRules();

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

  this.loadRules();
  this.toggleSidebar('edit')



  
}


async updateGptData(){


  
  //const gpt_key = document.querySelector("#openAIAPIKeyInp");
  const api_key = document.getElementById("openApiKey").value;  
  const usage_value = document.getElementById("usageLimit").value;
  const is_gpt_active = this.state.isChatGPTConfigActive
      

  

  let gpt_update = await jsonrpc('/web/dataset/call_kw', {
    model: 'vex.gpt.config',
    method: 'update_gpt_config',
    args: [],  
    kwargs: {
      enable_gpt_responder: is_gpt_active,
      chatgpt_key: api_key,
      daily_usage_limit: usage_value
    }
  });

  console.log(gpt_update);
  this.toggleSidebar('right');

  
  

}


}

registry.category("actions").add("vex_sync_mercado_libre.chatbot", ChatbotTemplate);
