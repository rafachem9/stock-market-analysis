// =============================================================================
// Jenkinsfile - Stock Market Analysis
// Descarga, prueba y rollback automático si falla
// =============================================================================

pipeline {
    agent any
    
    environment {
        // =============================================
        // CONFIGURACIÓN - MODIFICAR SEGÚN TU ENTORNO
        // =============================================
        
        PROJECT_DIR = '/home/rafachem9/data-engineer/stock-market-analysis'
        VENV_PYTHON = "${PROJECT_DIR}/.venv/bin/python"
        GIT_BRANCH = 'dev-cursor'
    }
    
    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 20, unit: 'MINUTES')
        timestamps()
    }
    
    stages {
        stage('Backup') {
            steps {
                echo '💾 Guardando versión actual para posible rollback...'
                dir("${PROJECT_DIR}") {
                    sh '''
                        # Guardar el commit actual
                        git rev-parse HEAD > /tmp/stock_analysis_last_commit.txt
                        echo "Commit actual: $(cat /tmp/stock_analysis_last_commit.txt)"
                    '''
                }
            }
        }
        
        stage('Actualizar') {
            steps {
                echo '📥 Descargando última versión...'
                dir("${PROJECT_DIR}") {
                    sh '''
                        git fetch origin ${GIT_BRANCH}
                        git checkout ${GIT_BRANCH}
                        git pull origin ${GIT_BRANCH}
                        
                        echo "✅ Actualizado a: $(git log -1 --oneline)"
                    '''
                }
            }
        }
        
        stage('Instalar Dependencias') {
            steps {
                echo '📦 Instalando dependencias...'
                dir("${PROJECT_DIR}") {
                    sh '''
                        ${VENV_PYTHON} -m pip install -r requirements.txt --quiet
                    '''
                }
            }
        }
        
        stage('Test Imports') {
            steps {
                echo '🧪 Verificando imports...'
                dir("${PROJECT_DIR}/src") {
                    sh '''
                        ${VENV_PYTHON} -c "
import sys
sys.path.insert(0, '.')

# Test imports principales
from config import DATA_DIR, TELEGRAM_BOT_TOKEN
from etl.variables import ibex35_tickers, tickers_sp500
from etl.functions import extraction_historic, analysis_stock_hist
from etl.alerts import AlertManager
from etl.get_index_data import get_index

print('✅ Todos los imports correctos')
"
                    '''
                }
            }
        }
        
        stage('Test Dashboard') {
            steps {
                echo '🧪 Verificando dashboard...'
                dir("${PROJECT_DIR}/src") {
                    sh '''
                        ${VENV_PYTHON} -c "
import streamlit
import plotly
import pandas as pd
from pathlib import Path

# Verificar que se puede cargar el dashboard
exec(open('dashboard.py').read().split('if __name__')[0])
print('✅ Dashboard OK')
"
                    '''
                }
            }
        }
        
        stage('Test Ejecución') {
            steps {
                echo '🧪 Probando ejecución del análisis...'
                dir("${PROJECT_DIR}/src") {
                    sh '''
                        # Test rápido: solo verificar que main.py arranca sin errores de sintaxis
                        ${VENV_PYTHON} -m py_compile main.py
                        ${VENV_PYTHON} -m py_compile config.py
                        ${VENV_PYTHON} -m py_compile etl/functions.py
                        ${VENV_PYTHON} -m py_compile etl/alerts.py
                        
                        echo "✅ Sintaxis correcta en todos los archivos"
                    '''
                }
            }
        }
    }
    
    post {
        success {
            echo '''
╔═══════════════════════════════════════════╗
║  ✅ ACTUALIZACIÓN EXITOSA                  ║
╠═══════════════════════════════════════════╣
║  Todos los tests pasaron correctamente.   ║
║  La nueva versión está lista para usar.   ║
╚═══════════════════════════════════════════╝
            '''
        }
        
        failure {
            echo '❌ Tests fallidos. Iniciando rollback...'
            dir("${PROJECT_DIR}") {
                sh '''
                    echo "🔄 Restaurando versión anterior..."
                    
                    LAST_COMMIT=$(cat /tmp/stock_analysis_last_commit.txt 2>/dev/null || echo "")
                    
                    if [ -n "$LAST_COMMIT" ]; then
                        git checkout $LAST_COMMIT
                        echo "✅ Rollback completado a: $LAST_COMMIT"
                    else
                        echo "⚠️ No se pudo hacer rollback, commit anterior no encontrado"
                    fi
                '''
            }
            echo '''
╔═══════════════════════════════════════════╗
║  ⚠️ ROLLBACK EJECUTADO                     ║
╠═══════════════════════════════════════════╣
║  La actualización falló.                  ║
║  Se ha restaurado la versión anterior.    ║
║  Revisa los logs para más detalles.       ║
╚═══════════════════════════════════════════╝
            '''
        }
    }
}
