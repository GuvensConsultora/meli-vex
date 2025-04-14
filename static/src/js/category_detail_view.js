/** @odoo-module **/
import { Component, useState, onWillStart, useEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

class MiComponenteOWL extends Component {
    static template = "odoo-mercadolibre.MiComponenteOWL";

    setup() {
        this.env = useEnv();
        this.action = useService("action");
        this.user = useService("user");  
        this.router = useService("router");
        this.orm = useService("orm");  // Asegúrate de que `orm` está definido

        this.state = useState({
            trendingKeywords: []
        });

        // 🔍 Depuración: imprimir TODO para ver dónde está el ID
        console.log("🔍 searchParams:", this.env.searchParams);
        console.log("🔍 user.context:", this.user.context);
        console.log("🔍 router.currentParams:", this.router.currentParams);

        // ✅ Buscar el ID en todas partes
        this.categoryId = this.env.searchParams?.params?.category_id 
                        || this.user.context?.category_id 
                        || this.router.currentParams?.category_id
                        || null;

        console.log("📌 ID de la categoría recibida:", this.categoryId);

        onWillStart(this.fetchTrendingKeywords.bind(this));
    }

    async fetchTrendingKeywords() {
        try {
            if (!this.categoryId) {
                console.warn("⚠️ No se recibió category_id, no se pueden filtrar los datos.");
                return;
            }

            const result = await this.orm.searchRead("vex.category.trending.keyword", 
                [["category_id", "=", this.categoryId]],  
                ["id", "keyword"]
            );

            this.state.trendingKeywords.splice(0, this.state.trendingKeywords.length, ...result);

            console.log("📌 Palabras más buscadas para la categoría", this.categoryId, this.state.trendingKeywords);
        } catch (error) {
            console.error("❌ Error al obtener palabras más buscadas:", error);
        }
    }

    goBack() {
        window.history.back();
    }
}

registry.category("actions").add("mi_componente_owl", MiComponenteOWL);
