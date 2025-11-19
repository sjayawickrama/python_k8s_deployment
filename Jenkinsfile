pipeline {
    agent any

    // 1. Define input parameters to receive data from the Generic Webhook Trigger
    parameters {
        string(name: 'HEAD_REF', defaultValue: 'master', description: 'Source branch name for the PR build')
        string(name: 'HEAD_SHA', defaultValue: 'HEAD', description: 'Commit SHA to checkout for the PR build')
        string(name: 'PULL_REQUEST_ID', defaultValue: '0', description: 'The GitHub Pull Request number')
    }

    // 2. Remove the 'githubPush()' trigger since we rely on the job-level Generic Webhook Trigger
    // triggers {
    //     githubPush() // This line is removed!
    // }

    // Define the temporary VENV path once using Jenkins environment variables
    environment {
        // Use a safe, unique path in /tmp for the venv
        VENV_DIR = "/tmp/venv-${UUID.randomUUID()}"
        // Set dynamic tag based on PR number or commit short SHA for Docker image
        // We use the first 7 characters of the SHA for the tag
        DOCKER_TAG = "${params.PULL_REQUEST_ID}-${params.HEAD_SHA.substring(0, 7)}"
    }

    stages {
        stage('Git Checkout') {
            steps {
                // IMPORTANT: Checkout using the dynamic HEAD_SHA provided by the webhook.
                // This ensures we build the exact commit associated with the PR.
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: "${params.HEAD_REF}"]],
                    userRemoteConfigs: [[url: 'https://github.com/sjayawickrama/python_k8s_deployment.git']],
                    // Use the SHA to get the exact state
                    changelog: false,
                    poll: false,
                    doGenerateSubmoduleConfigurations: false,
                    extensions: [[$class: 'ChangelogToBranch', branch: "${params.HEAD_REF}"]]
                ])

                // If using the simple 'git' step, you'd check out the SHA like this:
                sh "git checkout -f ${params.HEAD_SHA}"
            }
        }

        stage('Install Dependencies') {
            steps {
                dir('my_new_project') {
                    // 1. Create the virtual environment
                    sh "python3 -m venv ${VENV_DIR}"

                    // 2. Install dependencies
                    sh "${VENV_DIR}/bin/pip install -r requirements.txt"
                }
            }
        }

        stage('Unit Test') {
            steps {
                dir('my_new_project') {
                    // Run tests
                    sh "${VENV_DIR}/bin/python -m pytest"
                }
            }
        }

        stage('Docker Build & Tag') {
            steps {
                dir('my_new_project') {
                    script {
                        withDockerRegistry(credentialsId: 'docker-cred', toolName: 'docker') {
                            // Use the dynamic DOCKER_TAG defined in the environment block
                            sh "docker build -t sjayawickrama89/frontend_python:${env.DOCKER_TAG} ."
                            // Push the newly tagged image
                            sh "docker push sjayawickrama89/frontend_python:${env.DOCKER_TAG}"
                        }
                    }
                }
            }
        }
        
        // Ensure this stage is updated to use the dynamic DOCKER_TAG
        stage('Docker Push Latest (If Merged)') {
             when { expression { return params.action == 'closed' && params.pull_request.merged == 'true' } }
             steps {
                 dir('my_new_project') {
                     script {
                         withDockerRegistry(credentialsId: 'docker-cred', toolName: 'docker') {
                            // Tag the just-built image with 'latest' and push it
                            sh "docker tag sjayawickrama89/frontend_python:${env.DOCKER_TAG} sjayawickrama89/frontend_python:latest"
                            sh "docker push sjayawickrama89/frontend_python:latest"
                         }
                     }
                 }
             }
        }

        stage('Cleanup') {
            // Cleanup now happens in the post section for reliable execution
            steps {
                sh "rm -rf ${VENV_DIR}"
            }
        }
    }
}
