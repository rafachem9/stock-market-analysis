# Guía de Indicadores de Inversión

Esta guía explica los indicadores más relevantes que genera el sistema y cómo interpretarlos para tomar mejores decisiones de inversión.

---

## 📊 Indicadores Clave

### 1. Investment Score (Score de Inversión)

**Qué es:** Un score compuesto de 0-100 que combina múltiples factores para identificar oportunidades.

**Cómo se calcula:**
- Base: 50 puntos
- Rentabilidad prevista > 20%: +20 puntos
- Rentabilidad prevista > 10%: +10 puntos
- Sharpe Ratio > 2: +15 puntos
- Sharpe Ratio > 1: +10 puntos
- Dividend Yield > 5%: +10 puntos
- Alpha positivo: hasta +10 puntos
- Alta volatilidad: -10 puntos

**Interpretación:**
| Score | Interpretación |
|-------|---------------|
| 80-100 | Excelente oportunidad |
| 65-79 | Buena oportunidad |
| 50-64 | Neutral |
| 35-49 | Precaución |
| 0-34 | Alto riesgo |

---

### 2. Rentabilidad Prevista

**Qué es:** Diferencia porcentual entre el precio actual y el precio objetivo medio de los analistas.

**Fórmula:**
```
Rentabilidad Prevista = ((Precio Objetivo - Precio Actual) / Precio Actual) * 100
```

**Interpretación:**
| Valor | Significado |
|-------|-------------|
| > 30% | Muy infravalorada (verificar por qué) |
| 15-30% | Potencial de subida significativo |
| 5-15% | Ligera infravaloración |
| -5% a 5% | Valoración justa |
| < -5% | Posiblemente sobrevalorada |

**⚠️ Precaución:** Una rentabilidad prevista muy alta puede indicar problemas (la acción ha caído por una razón).

---

### 3. Sharpe Ratio

**Qué es:** Mide el rendimiento ajustado al riesgo. Cuánto retorno extra obtienes por cada unidad de riesgo.

**Fórmula:**
```
Sharpe Ratio = (Retorno Medio - Tasa Libre de Riesgo) / Volatilidad
```

**Interpretación:**
| Valor | Calificación |
|-------|--------------|
| > 3 | Excelente |
| 2-3 | Muy bueno |
| 1-2 | Bueno |
| 0-1 | Aceptable |
| < 0 | Malo (pérdidas) |

**Uso práctico:** Preferir acciones con Sharpe alto cuando quieras minimizar riesgo.

---

### 4. Alpha (α)

**Qué es:** El exceso de retorno de una acción respecto a lo que predice su riesgo (beta).

**Interpretación:**
| Valor | Significado |
|-------|-------------|
| > 0 | La acción supera al mercado |
| = 0 | Rendimiento igual al esperado |
| < 0 | La acción rinde menos que el mercado |

**Ejemplo:** Alpha de 0.05 significa que la acción rinde 5% más de lo esperado dado su nivel de riesgo.

---

### 5. Beta (β)

**Qué es:** Mide la sensibilidad de la acción respecto al mercado.

**Interpretación:**
| Valor | Comportamiento |
|-------|----------------|
| β > 1.5 | Muy volátil (amplifica movimientos del mercado) |
| β = 1 | Se mueve igual que el mercado |
| 0.5 < β < 1 | Menos volátil que el mercado |
| β < 0.5 | Defensiva (baja correlación con mercado) |
| β < 0 | Inversa (raro, se mueve contrario al mercado) |

**Uso práctico:**
- Mercado alcista: Preferir β > 1 (más ganancia)
- Mercado bajista: Preferir β < 1 (menos pérdida)

---

### 6. Dividend Yield

**Qué es:** Rentabilidad por dividendo anual respecto al precio de la acción.

**Fórmula:**
```
Dividend Yield = (Dividendo Anual / Precio Acción) * 100
```

**Interpretación:**
| Valor | Evaluación |
|-------|------------|
| > 6% | Muy alto (verificar sostenibilidad) |
| 4-6% | Alto |
| 2-4% | Moderado |
| 1-2% | Bajo |
| < 1% | Mínimo o sin dividendos |

**⚠️ Precaución:** Dividendos muy altos pueden ser insostenibles o indicar problemas.

---

### 7. RSI (Relative Strength Index)

**Qué es:** Indicador de momentum que mide la velocidad y cambio de movimientos de precio.

**Interpretación:**
| Valor | Señal |
|-------|-------|
| < 30 | **Sobrevendido** - Posible oportunidad de compra |
| 30-70 | Neutral |
| > 70 | **Sobrecomprado** - Posible señal de venta |

**Uso práctico:** Combinar con otros indicadores. RSI bajo + buenos fundamentales = buena oportunidad.

---

### 8. P/E Ratio (Price to Earnings)

**Qué es:** Cuánto pagas por cada euro de beneficio de la empresa.

**Tipos:**
- **Trailing P/E:** Basado en beneficios pasados
- **Forward P/E:** Basado en beneficios estimados futuros

**Interpretación:**
| Valor | Evaluación |
|-------|------------|
| < 10 | Posiblemente infravalorada |
| 10-20 | Valoración razonable |
| 20-30 | Cara (normal en growth) |
| > 30 | Muy cara (verificar crecimiento) |
| Negativo | Pérdidas (precaución) |

**⚠️ Importante:** Comparar siempre con empresas del mismo sector.

---

### 9. Volatilidad

**Qué es:** Desviación estándar de los retornos diarios. Mide cuánto fluctúa el precio.

**Interpretación:**
| Valor | Riesgo |
|-------|--------|
| < 1.5% | Baja volatilidad |
| 1.5-3% | Moderada |
| 3-5% | Alta |
| > 5% | Muy alta |

---

## 🎯 Estrategias de Inversión

### Estrategia 1: Value Investing (Inversión en Valor)
**Buscar:**
- Rentabilidad prevista > 15%
- P/E < 15
- Dividend Yield > 2%
- Sharpe Ratio > 1

### Estrategia 2: Dividendos
**Buscar:**
- Dividend Yield > 4%
- Dividendo sostenible (historial estable)
- P/E razonable (< 20)

### Estrategia 3: Momentum
**Buscar:**
- RSI en zona de sobreventa (< 35)
- Alpha positivo
- Retorno 1-3 meses positivo

### Estrategia 4: Bajo Riesgo
**Buscar:**
- Beta < 0.8
- Volatilidad < 2%
- Sharpe Ratio > 1.5
- Sector defensivo (utilities, consumo básico)

---

## 📋 Checklist Antes de Invertir

1. ☐ **Investment Score** > 65
2. ☐ **Rentabilidad prevista** positiva y realista
3. ☐ **Sharpe Ratio** > 1
4. ☐ **P/E** razonable para el sector
5. ☐ **Volatilidad** aceptable para tu perfil de riesgo
6. ☐ **Sector** en tendencia positiva
7. ☐ **Noticias recientes** verificadas
8. ☐ **Diversificación** - no concentrar en un solo valor

---

## ⚠️ Disclaimer

Esta información es solo para fines educativos. No constituye asesoramiento financiero. Siempre haz tu propia investigación antes de invertir.

---

## 📚 Glosario Rápido

| Término | Definición |
|---------|------------|
| Alcista (Bull) | Mercado/tendencia al alza |
| Bajista (Bear) | Mercado/tendencia a la baja |
| Benchmark | Índice de referencia (IBEX, S&P 500) |
| Capitalización | Valor total de mercado de una empresa |
| Drawdown | Caída desde máximo histórico |
| Ex-Dividend | Fecha desde la que no tienes derecho al próximo dividendo |
| Growth | Empresa de alto crecimiento |
| Value | Empresa infravalorada por el mercado |
