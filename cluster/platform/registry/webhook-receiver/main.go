package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	batchv1 "k8s.io/api/batch/v1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
)

// GiteaWebhook represents the webhook payload from Gitea
type GiteaWebhook struct {
	Ref        string `json:"ref"`
	Repository struct {
		Name     string `json:"name"`
		CloneURL string `json:"clone_url"`
		SSHURL   string `json:"ssh_url"`
	} `json:"repository"`
	HeadCommit struct {
		ID string `json:"id"`
	} `json:"head_commit"`
}

var k8sClient *kubernetes.Clientset

func main() {
	// Create Kubernetes client
	config, err := rest.InClusterConfig()
	if err != nil {
		log.Fatalf("Failed to get in-cluster config: %v", err)
	}

	k8sClient, err = kubernetes.NewForConfig(config)
	if err != nil {
		log.Fatalf("Failed to create Kubernetes client: %v", err)
	}

	http.HandleFunc("/webhook", handleWebhook)
	http.HandleFunc("/health", healthCheck)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("Starting webhook receiver on port %s", port)
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}

func healthCheck(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, "OK")
}

func handleWebhook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var webhook GiteaWebhook
	if err := json.NewDecoder(r.Body).Decode(&webhook); err != nil {
		log.Printf("Failed to decode webhook: %v", err)
		http.Error(w, "Invalid payload", http.StatusBadRequest)
		return
	}

	// Only build on push to main branch
	if webhook.Ref != "refs/heads/main" {
		log.Printf("Ignoring webhook for ref: %s", webhook.Ref)
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, "Ignoring non-main branch")
		return
	}

	appName := webhook.Repository.Name
	commitSHA := webhook.HeadCommit.ID[:7] // Short SHA
	imageTag := commitSHA

	// Use internal Gitea URL
	gitURL := strings.Replace(webhook.Repository.CloneURL, "https://", "http://", 1)
	gitURL = strings.Replace(gitURL, "gitea.home.mcztest.com", "gitea-http.gitea.svc.cluster.local:3000", 1)

	log.Printf("Triggering build for %s:%s (git: %s)", appName, imageTag, gitURL)

	// Create Kubernetes Job
	job := createBuildJob(appName, gitURL, "main", imageTag, "./Dockerfile")

	ctx := context.Background()
	_, err := k8sClient.BatchV1().Jobs("container-registry").Create(ctx, job, metav1.CreateOptions{})
	if err != nil {
		log.Printf("Failed to create build job: %v", err)
		http.Error(w, "Failed to create build job", http.StatusInternalServerError)
		return
	}

	log.Printf("Build job created successfully for %s:%s", appName, imageTag)
	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, "Build job created for %s:%s", appName, imageTag)
}

func createBuildJob(appName, gitURL, branch, imageTag, dockerfilePath string) *batchv1.Job {
	jobName := fmt.Sprintf("build-%s-%s", appName, imageTag)
	ttl := int32(3600) // 1 hour

	return &batchv1.Job{
		ObjectMeta: metav1.ObjectMeta{
			Name:      jobName,
			Namespace: "container-registry",
			Labels: map[string]string{
				"app":      "build-job",
				"app-name": appName,
			},
		},
		Spec: batchv1.JobSpec{
			TTLSecondsAfterFinished: &ttl,
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{
						"app": "build-job",
					},
				},
				Spec: corev1.PodSpec{
					RestartPolicy: corev1.RestartPolicyNever,
					Containers: []corev1.Container{
						{
							Name:  "kaniko",
							Image: "gcr.io/kaniko-project/executor:latest",
							Args: []string{
								fmt.Sprintf("--dockerfile=%s", dockerfilePath),
								fmt.Sprintf("--context=git://%s#refs/heads/%s", gitURL, branch),
								fmt.Sprintf("--destination=registry.home.mcztest.com/%s:%s", appName, imageTag),
								"--insecure",
								"--skip-tls-verify",
								"--cache=true",
								"--cache-repo=registry.home.mcztest.com/cache",
							},
							VolumeMounts: []corev1.VolumeMount{
								{
									Name:      "docker-config",
									MountPath: "/kaniko/.docker/",
								},
							},
						},
					},
					Volumes: []corev1.Volume{
						{
							Name: "docker-config",
							VolumeSource: corev1.VolumeSource{
								EmptyDir: &corev1.EmptyDirVolumeSource{},
							},
						},
					},
				},
			},
		},
	}
}
