/** @odoo-module **/

import { Component, onWillUnmount, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

class InboxTemplate extends Component {
  static template = "vex_sync_mercado_libre.questions";

  async setup() {
    super.setup();
    this.orm = useService("orm");
    this.notificationService = useService("notification");

    this.state = useState({
      title: "",
      description: "",
      socialMedia: "WhatsApp",
      segments: [],
      selectedSegment: null,
      message: [],
    });
    // Inicializar los "segmentos" (partners) al montar el componente
    onWillStart(async () => {
      await this.fetchPartnersAsSegments();
      this.addBackground();
      this.loadMessages();

      document.addEventListener("DOMContentLoaded", function () {
        const eventSource = new EventSource("/whatsapp/stream");
        eventSource.onmessage = function (event) {
          const data = JSON.parse(event.data);
          console.log("New WhatsApp message received:", data);
          // Actualiza la UI aquí
        };
        eventSource.onerror = function (event) {
          console.error("Failed to connect to event stream", event);
        };
      });
    });

    onWillUnmount(() => {
      this.delBackground();
    });

    await this.loadCSS("vex_sync_mercado_libre/static/src/css/fontawesome.min.css");
    // await this.loadCSS("/whatsapp_suite/static/plugin/czm-chat-support.css");
    // // Cargar JavaScript
    // await this.loadScript("/whatsapp_suite/static/plugin/components/jquery/jquery-1.9.0.min.js");
    // await this.loadScript("/whatsapp_suite/static/plugin/components/moment/moment.min.js");
    // await this.loadScript("/whatsapp_suite/static/plugin/components/moment/moment-timezone-with-data.min.js");
    // await this.loadScript("/whatsapp_suite/static/plugin/czm-chat-support.min.js");
    // await this.initializeChatPlugin();
  }

  _handleNotification(payload) {
    // Mostrar una notificación cada vez que se recibe un mensaje
    this.notificationService.add(
      _t("Nuevo mensaje de WhatsApp: " + payload.body),
      {
        type: "info",
        title: _t("WhatsApp"),
        sticky: false,
      }
    );
  }

  async loadMessages() {
    try {
      const response = await fetch("/whatsapp/webhook", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ someData: "example" }),
      });
      if (!response.ok) {
        console.error("HTTP error!", response.status, await response.text());
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const messages = await response.json();
      // this.state.messages = messages.map(msg => ({
      //     id: msg.id,
      //     text: msg.text.body,
      //     timestamp: new Date(msg.timestamp * 1000).toLocaleTimeString(),
      //     is_sender: msg.from === "your_whatsapp_number", // Adjust based on your needs
      // }));
      console.log(messages);
    } catch (error) {
      console.error("Error fetching messages:", error);
    }
  }

  addBackground() {
    const actionManagerEl = document.querySelector(".o_action_manager");
    if (actionManagerEl) {
      actionManagerEl.id = "doodles";
      actionManagerEl.classList.add("list-contact");
    } else {
      console.warn("Elemento .o_action_manager no encontrado.");
    }
  }

  delBackground() {
    const actionManagerEl = document.querySelector(".o_action_manager");
    if (actionManagerEl.id == "doodles") {
      actionManagerEl.id = null;
      actionManagerEl.classList.remove("list-contact");
    } else {
      console.warn("Elemento .o_action_manager no encontrado.");
    }
  }

  loadCSS(url) {
    return new Promise(function (resolve, reject) {
      let link = document.createElement("link");
      link.type = "text/css";
      link.rel = "stylesheet";
      link.onload = () => {
        let fileName = url.match(/[^\/]+$/)[0];
        let scriptMessage = "Css cargado correctamente";
        let fileMessage = `${fileName}`;
        console.info(
          `%c${scriptMessage}%c${fileMessage}`,
          "background: #00BFFF; color: #000000; border-radius: 8px 0 0 8px; padding: 4px 8px; font-family: Arial, sans-serif; font-size: 12px;",
          "background: #FFFFFF; color: #000000; border-radius: 0 8px 8px 0; padding: 4px 8px; font-family: Arial, sans-serif; font-size: 12px;"
        );
        resolve();
      };
      link.href = url;
      document.head.appendChild(link);
    });
  }

  loadScript(url) {
    return new Promise((resolve, reject) => {
      let script = document.createElement("script");
      script.src = url;
      script.onload = () => {
        let fileName = url.match(/[^\/]+$/)[0];
        let scriptMessage = "Script cargado correctamente";
        let fileMessage = `${fileName}`;

        // Estilizando y mostrando el mensaje en la consola
        console.info(
          `%c${scriptMessage}%c${fileMessage}`,
          "background: #FFD700; color: #000000; border-radius: 8px 0 0 8px; padding: 4px 8px; font-family: Arial, sans-serif; font-size: 12px;",
          "background: #FFFFFF; color: #000000; border-radius: 0 8px 8px 0; padding: 4px 8px; font-family: Arial, sans-serif; font-size: 12px;"
        );
        resolve();
      };
      script.onerror = () =>
        reject(new Error(`Error al cargar el script: ${url}`));
      document.body.appendChild(script);
    });
  }

  async cargarImagenDinamica(partnerId) {
    try {
      // Construir la URL para la imagen del partner
      const imageUrl = `/web/image?model=res.partner&field=avatar_128&id=${partnerId}`;

      // Actualizar el src del elemento de imagen en tu widget/plugin
      // Asumiendo que tienes una forma de seleccionar el elemento de imagen adecuado, por ejemplo:
      document.querySelector("#tuElementoDeImagen").src = imageUrl;
    } catch (error) {
      console.error("Error cargando la imagen dinámicamente:", error);
    }
  }

  // Llamar a la función con el ID del partner deseado
  // cargarImagenDinamica(tuPartnerId);

  async initializeChatPlugin() {
    // Esperar a que jQuery esté disponible
    if (typeof $ !== "undefined") {
      // Aquí puedes inicializar el plugin czmChatSupport como lo harías normalmente
      $("#czm-chat-container").czmChatSupport({
        /* Button Settings */
        button: {
          position:
            "right" /* left, right or false. "position:false" does not pin to the left or right */,
          style: 7 /* Button style. Number between 1 and 7 */,
          src: '<img src="/web/image?model=res.partner&field=avatar_128&id=62" alt="">', // Ruta actualizada
          backgroundColor: "#10c379" /* Html color code */,
          effect: 1 /* Button effect. Number between 1 and 7 */,
          notificationNumber: false /* Custom text or false. To remove, (notificationNumber:false) */,
          speechBubble: false /* To remove, (speechBubble:false) */,
          pulseEffect: false /* To remove, (pulseEffect:false) */,
          text: {
            /* For Button style larger than 1 */
            title: "Whatsapp Support Service" /* Writing is required */,
            description:
              "Mon-Sat: 10:00/22:00" /* To remove, (description:false) */,
            online: "Now Online" /* To remove, (online:false) */,
            offline: "I will be back soon" /* To remove, (offline:false) */,
          },
          link: {
            desktop:
              "https://web.whatsapp.com/send?phone=905377323226&text=Hi" /* Writing is required */,
            mobile:
              "https://wa.me/905377323226/?text=Hi" /* If it is hidden desktop link will be valid. To remove, (mobile:false) */,
          },
          onlineDay: {
            /* Change the day you are offline like this. (sunday:false) */
            sunday: "00:00-23:59",
            monday: "00:00-23:59",
            tuesday: "00:00-23:59",
            wednesday: "00:00-23:59",
            thursday: "00:00-23:59",
            friday: "00:00-23:59",
            saturday: "00:00-23:59",
          },
        },

        /* Other Settings */
        sound: true /* true (default sound), false or custom sound. Custom sound example, (sound:'assets/sound/notification.mp3') */,
        changeBrowserTitle:
          "New Message!" /* Custom text or false. To remove, (changeBrowserTitle:false) */,
        cookie: false /* It does not show the speech bubble, notification number, pulse effect and automatic open popup again for the specified time. For example, do not show for 1 hour, (cookie:1) or to remove, (cookie:false) */,
      });
      let initializationMessage =
        "Plugin czmChatSupport inicializado correctamente.";
      console.info(
        `%c${initializationMessage}`,
        "background: #25D366; color: #000000; border-radius: 8px; padding: 4px 8px; font-family: Arial, sans-serif; font-size: 12px;"
      );
    } else {
      let errorMessage = "jQuery no está definido.";
      console.error(
        `%c${errorMessage}`,
        "background: #D32F2F; color: #FFFFFF; border-radius: 8px; padding: 4px 8px; font-family: Arial, sans-serif; font-size: 12px;"
      );
    }
  }

  randomChoice(items) {
    return items[Math.floor(Math.random() * items.length)];
  }

  // Adaptación para buscar 'partners' y considerarlos como 'segmentos'
  async fetchPartnersAsSegments() {
    // Nota: Aquí estamos usando 'name' e 'id', pero puedes ajustarlo según sea necesario
    const fields_to_fetch = [
      "id",
      "company_id",
      "create_date",
      "name",
      "title",
      "parent_id",
      "user_id",
      "state_id",
      "country_id",
      "industry_id",
      "color",
      "commercial_partner_id",
      "create_uid",
      "write_uid",
      // "complete_name",
      "ref",
      "lang",
      "tz",
      "vat",
      "company_registry",
      "website",
      "function",
      "type",
      "street",
      "street2",
      "zip",
      "city",
      "email",
      "phone",
      "mobile",
      "commercial_company_name",
      "company_name",
      "date",
      "comment",
      "partner_latitude",
      "partner_longitude",
      "active",
      "employee",
      "is_company",
      "partner_share",
      "write_date",
      "message_bounce",
      "email_normalized",
      "signup_type",
      "signup_expiration",
      "signup_token",
      // "calendar_last_notif_ack",
      "team_id",
      "partner_gid",
      "additional_info",
      "phone_sanitized",
    ];
    const partners = await this.orm.call("res.partner", "search_read", [[]], {
      fields: fields_to_fetch,
    });

    this.state.segments = partners.map((partner) => ({
      // Asigna cada 'partner' a un formato de 'segmento', si necesario
      id: partner.id,
      name: partner.name,
      socialMedia: this.randomChoice(["Instagram", "Facebook", "WhatsApp"]),
    }));
    console.log(this.state.segments);
  }
}

registry.category("actions").add("vex_sync_mercado_libre.questions", InboxTemplate);
// Component.env.qweb.registerComponent('WhatsAppSuiteComponent', InboxTemplate);
