// =============================================================================
// Jenkinsfile - Stock Market Analysis
// Descarga, prueba y rollback automático si falla
// =============================================================================

pipeline {
    agent any
    
    environment {
        // =============================================
        // CONFIGURACIÓN - BASADA EN EL WORKSPACE DE JENKINS
        // =============================================
        
        PROJECT_DIR = "${WORKSPACE}"
        VENV_PYTHON = "/home/rafachem9/repositories/repos-venv/stock-airflow"
        GIT_BRANCH = 'main'
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
                sh """
                    cd ${PROJECT_DIR}
                    git fetch origin ${GIT_BRANCH}
                    git checkout ${GIT_BRANCH}
                    git pull origin ${GIT_BRANCH}
                    
                    echo "✅ Actualizado a: \$(git log -1 --oneline)"
                """
            }
        }
        
        stage('Instalar Dependencias') {
            steps {
                echo '📦 Instalando dependencias...'
                sh """
                    cd ${PROJECT_DIR}
                    ${VENV_PYTHON} -m pip install -r requirements.txt --quiet
                """
            }
        }
        
        stage('Test Imports') {
            steps {
                echo '🧪 Verificando imports...'
                sh '''
                    cd ${PROJECT_DIR}/src
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
        
        stage('Test Dashboard') {
            steps {
                echo '🧪 Verificando dashboard...'
                sh '''
                    cd ${PROJECT_DIR}/src
                    ${VENV_PYTHON} -c "
import streamlit
import plotly
import pandas as pd
print('✅ Dashboard OK')
"
                '''
            }
        }
        
        stage('Test Sintaxis') {
            steps {
                echo '🧪 Verificando sintaxis...'
                sh """
                    cd ${PROJECT_DIR}/src
                    ${VENV_PYTHON} -m py_compile main.py
                    ${VENV_PYTHON} -m py_compile config.py
                    ${VENV_PYTHON} -m py_compile dashboard.py
                    ${VENV_PYTHON} -m py_compile etl/functions.py
                    ${VENV_PYTHON} -m py_compile etl/alerts.py
                    ${VENV_PYTHON} -m py_compile etl/get_index_data.py
                    ${VENV_PYTHON} -m py_compile etl/variables.py
                    
                    echo "✅ Sintaxis correcta en todos los archivos"
                """
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
            sh '''
                cd ${PROJECT_DIR}
                
                echo "🔄 Restaurando versión anterior..."
                
                if [ -f "${BACKUP_COMMIT_FILE}" ]; then
                    LAST_COMMIT=$(cat ${BACKUP_COMMIT_FILE})
                    git checkout $LAST_COMMIT
                    echo "✅ Rollback completado a: $LAST_COMMIT"
                else
                    echo "⚠️ No se pudo hacer rollback, archivo de backup no encontrado"
                fi
            '''
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
