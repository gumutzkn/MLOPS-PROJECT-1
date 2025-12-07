pipeline {
    agent any

    environment {
        // Jenkins Credentials'dan çekilenler (Gizli)
        GCP_PROJECT = credentials('gcp-project-id')
        GCS_BUCKET_NAME = credentials('gcp-bucket-name')

        // Diğer ayarlar
        GCP_REGION = 'us-central1'
        // Burada da interpolation var ama environment içinde olduğu için sorun değil.
        // Ancak aşağıda kullanırken dikkat edeceğiz.
        IMAGE_TAG = "gcr.io/${GCP_PROJECT}/ml-project:latest" 
        GCLOUD_PATH = '/var/jenkins_home/google-cloud-sdk/bin'
    }

    stages {
        stage('Checkout Code') {
            steps {
                checkout scmGit(branches: [[name: '*/main']], extensions: [], userRemoteConfigs: [[credentialsId: 'github-token', url: 'https://github.com/gumutzkn/MLOPS-PROJECT-1.git']])
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    echo 'Docker İmajı İnşa Ediliyor...'
                    // DÜZELTME: $ işaretinin önüne \ koyduk
                    sh "docker build -t \$IMAGE_TAG ."
                }
            }
        }

       stage('Train Model (in Container)') {
            steps {
                withCredentials([file(credentialsId: 'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                    script {
                        echo 'Eğitim Containerı Başlatılıyor...'
                        
                        // JSON dosyasını doğrudan volume mount ile container'a bağlıyoruz
                        // Bu yöntem shell escaping sorunlarını tamamen ortadan kaldırır
                        sh """
                        docker run --rm \
                        -v \$GOOGLE_APPLICATION_CREDENTIALS:/app/key.json:ro \
                        -e GOOGLE_APPLICATION_CREDENTIALS=/app/key.json \
                        -e GCS_BUCKET_NAME=\$GCS_BUCKET_NAME \
                        \$IMAGE_TAG \
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
                        // DÜZELTME: Tüm değişkenlerin başına \ eklendi
                        sh """
                        export PATH=\$PATH:${GCLOUD_PATH}
                        
                        gcloud auth activate-service-account --key-file="\$GOOGLE_APPLICATION_CREDENTIALS"
                        gcloud config set project \$GCP_PROJECT
                        gcloud auth configure-docker --quiet

                        docker push \$IMAGE_TAG
                        """
                    }
                }
            }
        }

        stage('Deploy to Cloud Run') {
            steps {
                withCredentials([file(credentialsId: 'gcp-key', variable: 'GOOGLE_APPLICATION_CREDENTIALS')]) {
                    script {
                        echo 'Cloud Run Deploy Başlıyor...'
                        // DÜZELTME: Tüm değişkenlerin başına \ eklendi
                        sh """
                        export PATH=\$PATH:${GCLOUD_PATH}
                        
                        gcloud auth activate-service-account --key-file="\$GOOGLE_APPLICATION_CREDENTIALS"
                        gcloud config set project \$GCP_PROJECT
                        
                        gcloud run deploy ml-project \
                            --image=\$IMAGE_TAG \
                            --platform=managed \
                            --region=\$GCP_REGION \
                            --allow-unauthenticated \
                            --port=8080 \
                            --memory=2Gi \
                            --set-env-vars GCS_BUCKET_NAME=\$GCS_BUCKET_NAME
                        """
                    }
                }
            }
        }
    }
}