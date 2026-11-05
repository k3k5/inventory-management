<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div class="card">
      <div class="card-header">
        <h3 class="card-title">{{ t('restocking.budget') }}</h3>
        <span class="budget-value">{{ formatMoney(budget) }}</span>
      </div>
      <input
        v-model.number="budget"
        type="range"
        :min="BUDGET_MIN"
        :max="BUDGET_MAX"
        :step="BUDGET_STEP"
        class="budget-slider"
        :aria-label="t('restocking.budget')"
      />
      <div class="slider-scale">
        <span>{{ formatMoney(BUDGET_MIN) }}</span>
        <span>{{ formatMoney(BUDGET_MAX) }}</span>
      </div>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.totalCost') }}</div>
          <div class="stat-value">{{ formatMoney(recommendation.total_cost) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.remaining') }}</div>
          <div class="stat-value">{{ formatMoney(recommendation.remaining_budget) }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.leadTime') }}</div>
          <div class="stat-value">{{ t('restocking.days', { count: recommendation.lead_time_days }) }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommended') }} ({{ recommendation.items.length }})</h3>
          <button class="place-order-btn" :disabled="!canPlaceOrder" @click="placeOrder">
            {{ placing ? t('restocking.placing') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="orderMessage" class="order-message success-message">
          {{ orderMessage }}
          <router-link to="/orders">{{ t('restocking.viewOrders') }}</router-link>
        </div>
        <div v-if="orderError" class="order-message error-message">{{ orderError }}</div>

        <p v-if="recommendation.items.length === 0" class="empty">{{ t('restocking.noItems') }}</p>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.item') }}</th>
                <th>{{ t('restocking.table.category') }}</th>
                <th>{{ t('restocking.table.demandGap') }}</th>
                <th>{{ t('restocking.table.quantity') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.cost') }}</th>
                <th>{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recommendation.items" :key="item.sku">
                <td><strong>{{ item.sku }}</strong></td>
                <td>{{ translateProductName(item.name) }}</td>
                <td>{{ item.category }}</td>
                <td>{{ item.demand_gap.toLocaleString() }}</td>
                <td>{{ item.quantity.toLocaleString() }}</td>
                <td>{{ formatMoney(item.unit_cost, 2) }}</td>
                <td><strong>{{ formatMoney(item.cost, 2) }}</strong></td>
                <td>{{ t('restocking.days', { count: item.lead_time_days }) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

const BUDGET_MIN = 0
const BUDGET_MAX = 100000
const BUDGET_STEP = 1000

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, translateProductName } = useI18n()

    const currencySymbol = computed(() => (currentCurrency.value === 'JPY' ? '¥' : '$'))
    const formatMoney = (value, digits = 0) =>
      currencySymbol.value +
      Number(value).toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })

    const budget = ref(25000)
    const loading = ref(true)
    const error = ref(null)
    const placing = ref(false)
    const orderMessage = ref('')
    const orderError = ref('')
    const recommendation = ref({ total_cost: 0, remaining_budget: 0, lead_time_days: 0, items: [] })

    let requestId = 0
    const loadRecommendations = async () => {
      const current = ++requestId
      try {
        const result = await api.getRestockRecommendations(budget.value)
        if (current !== requestId) return // a newer slider value superseded this response
        recommendation.value = result
        error.value = null
      } catch (err) {
        if (current !== requestId) return
        error.value = 'Failed to load recommendations: ' + err.message
      } finally {
        if (current === requestId) loading.value = false
      }
    }

    let debounceTimer = null
    watch(budget, () => {
      orderMessage.value = ''
      orderError.value = ''
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(loadRecommendations, 150)
    })

    const canPlaceOrder = computed(() => !placing.value && recommendation.value.items.length > 0)

    const placeOrder = async () => {
      placing.value = true
      orderMessage.value = ''
      orderError.value = ''
      try {
        const order = await api.placeRestockOrder(budget.value)
        orderMessage.value = t('restocking.orderPlaced', {
          number: order.order_number,
          days: order.lead_time_days
        })
      } catch (err) {
        orderError.value = err.response?.data?.detail || t('restocking.orderFailed')
      } finally {
        placing.value = false
      }
    }

    onMounted(loadRecommendations)

    return {
      t,
      BUDGET_MIN,
      BUDGET_MAX,
      BUDGET_STEP,
      budget,
      loading,
      error,
      placing,
      orderMessage,
      orderError,
      recommendation,
      canPlaceOrder,
      placeOrder,
      formatMoney,
      translateProductName
    }
  }
}
</script>

<style scoped>
.budget-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
}

.budget-slider {
  width: 100%;
  accent-color: #2563eb;
}

.slider-scale {
  display: flex;
  justify-content: space-between;
  color: #64748b;
  font-size: 0.813rem;
}

.place-order-btn {
  background: #0f172a;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0.625rem 1.25rem;
  font-weight: 600;
  cursor: pointer;
}

.place-order-btn:hover:not(:disabled) {
  background: #1e293b;
}

.place-order-btn:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.order-message {
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.success-message {
  background: #ecfdf5;
  color: #047857;
}

.success-message a {
  margin-left: 0.5rem;
  font-weight: 600;
  color: #047857;
}

.error-message {
  background: #fef2f2;
  color: #b91c1c;
}

.empty {
  color: #64748b;
}
</style>
