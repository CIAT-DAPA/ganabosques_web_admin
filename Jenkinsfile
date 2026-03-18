pipeline {
    agent any

    environment {
        server_name   = credentials('ganabosques_name')
        server_host   = credentials('ganabosques_host')
        ssh_key       = credentials('ganabosques')
        ssh_key_user  = credentials('ganabosques_user')
    }

    stages {

        stage('Connection to AWS server') {
            steps {
                script {
                    remote = [
                        allowAnyHosts: true,
                        identityFile: ssh_key,
                        user: ssh_key_user,
                        name: server_name,
                        host: server_host
                    ]
                }
            }
        }

        stage('Deploy Flask Web Admin') {
            steps {
                script {
                    sshCommand remote: remote, command: '''
                        set -e

                        CONDA_ENV_PATH="/home/ganabosques/.miniforge3/envs/admin/bin"
                        APP_DIR="/opt/ganabosques/admin/ganabosques_web_admin"
                        APP_PORT=5002

                        echo "Matando proceso en puerto $APP_PORT..."
                        fuser -k $APP_PORT/tcp || true

                        echo "Entrando a la carpeta del proyecto..."
                        cd $APP_DIR

                        echo "Haciendo pull del código..."
                        git pull origin main

                        echo "Instalando dependencias con conda env admin..."
                        $CONDA_ENV_PATH/pip install -r ./src/requirements.txt

                        echo "Levantando servicio Flask..."
                        cd src
                        nohup $CONDA_ENV_PATH/python app.py > app.log 2>&1 &

                        echo "Deploy finalizado correctamente."
                    '''
                }
            }
        }
    }

    post {
        failure {
            echo '❌ Deploy failed'
        }

        success {
            echo '✅ Everything went very well!!'
        }
    }
}
