pipeline {
    agent any

    environment {
        GCP_PROJECT = credentials('gcp-project-id')
        GCS_BUCKET_NAME = credentials('gcp-bucket-name')

        GCP_REGION = 'us-central1'
        IMAGE_TAG = "gcr.io/${GCP_PROJECT}/ml-project:latest"
        GCLOUD_PATH = '/var/jenkins_home/google-cloud-sdk/bin'
        
    }

    stages {
        stage('Checkout Code') {
            steps {
                echo 'GitHub reposundan kod çekiliyor...'
                checkout scmGit(branches: [[name: '*/main']], extensions: [], userRemoteConfigs: [[credentialsId: 'github-token', url: 'https://github.com/gumutzkn/MLOPS-PROJECT-1.git']])
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    echo 'Docker İmajı İnşa Ediliyor (Build)...'
                    // Sadece paketleme yapıyoruz, çalıştırma yok.
                    sh "docker build -t ${IMAGE_TAG} ."
                }
            }
        }

        stage('Train Model (in Container)') {
            steps {
                withCredentials([file(credentialsId: 'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                    script {
                        echo 'Eğitim Containerı Başlatılıyor...'
                        
                        // --rm: İş bitince container silinir.
                        // -v: Key dosyasını container içine yansıtır (Mount).
                        // -e: Key dosyasının yerini Python'a söyler.
                        // python pipeline/training_pipeline.py: Senin eğitim kodunu çalıştırır.
                        sh """
                        docker run --rm \
                        -v ${GOOGLE_APPLICATION_CREDENTIALS}:/app/key.json \
                        -e GOOGLE_APPLICATION_CREDENTIALS=/app/key.json \
                        -e GCS_BUCKET_NAME=${GCS_BUCKET_NAME} \
                        ${IMAGE_TAG} \
                        python pipeline/training_pipeline.py
                        """
                    }
                }
            }
        }

        stage('Push Image to GCR') {
            steps {
                withCredentials([file(credentialsId: 'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                    script {
                        echo 'İmaj Google Container Registry\'ye yükleniyor...'
                        sh """
                        export PATH=\$PATH:${GCLOUD_PATH}
                        
                        # Gcloud login
                        gcloud auth activate-service-account --key-file="${GOOGLE_APPLICATION_CREDENTIALS}"
                        gcloud config set project ${GCP_PROJECT}
                        gcloud auth configure-docker --quiet

                        # Push
                        docker push ${IMAGE_TAG}
                        """
                    }
                }
            }
        }

        stage('Deploy to Cloud Run') {
            steps {
                withCredentials([file(credentialsId: 'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                    script {
                        echo 'Deploy...'
                        sh """
                        export PATH=\$PATH:${GCLOUD_PATH}
                        gcloud auth activate-service-account --key-file="${GOOGLE_APPLICATION_CREDENTIALS}"
                        gcloud config set project ${GCP_PROJECT}
                        
                        gcloud run deploy ml-project \
                            --image=${IMAGE_TAG} \
                            --platform=managed \
                            --region=${GCP_REGION} \
                            --allow-unauthenticated \
                            --port=8080 \
                            --memory=2Gi \
                            --set-env-vars GCS_BUCKET_NAME=${GCS_BUCKET_NAME}
                        """
                    }
                }
            }
        }
    }
}