package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/gorilla/mux"
)

type App struct {
	Name        string    `json:"name"`
	URL         string    `json:"url"`
	Description string    `json:"description"`
	Category    string    `json:"category"`
	CreatedAt   time.Time `json:"created_at"`
}

type Registry struct {
	mu       sync.RWMutex
	apps     map[string]App
	dataFile string
}

func NewRegistry(dataFile string) *Registry {
	r := &Registry{
		apps:     make(map[string]App),
		dataFile: dataFile,
	}
	r.load()
	return r
}

func (r *Registry) load() {
	data, err := os.ReadFile(r.dataFile)
	if err != nil {
		if os.IsNotExist(err) {
			return
		}
		log.Printf("Error loading data: %v", err)
		return
	}

	if err := json.Unmarshal(data, &r.apps); err != nil {
		log.Printf("Error unmarshaling data: %v", err)
	}
}

func (r *Registry) save() error {
	r.mu.RLock()
	defer r.mu.RUnlock()

	data, err := json.MarshalIndent(r.apps, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(r.dataFile, data, 0644)
}

func (r *Registry) ListApps(w http.ResponseWriter, req *http.Request) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	apps := make([]App, 0, len(r.apps))
	for _, app := range r.apps {
		apps = append(apps, app)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(apps)
}

func (r *Registry) CreateApp(w http.ResponseWriter, req *http.Request) {
	var app App
	if err := json.NewDecoder(req.Body).Decode(&app); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	if app.Name == "" || app.URL == "" {
		http.Error(w, "name and url are required", http.StatusBadRequest)
		return
	}

	app.CreatedAt = time.Now()

	r.mu.Lock()
	r.apps[app.Name] = app
	r.mu.Unlock()

	if err := r.save(); err != nil {
		log.Printf("Error saving data: %v", err)
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(app)
}

func (r *Registry) GetApp(w http.ResponseWriter, req *http.Request) {
	vars := mux.Vars(req)
	name := vars["name"]

	r.mu.RLock()
	app, exists := r.apps[name]
	r.mu.RUnlock()

	if !exists {
		http.Error(w, "app not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(app)
}

func (r *Registry) DeleteApp(w http.ResponseWriter, req *http.Request) {
	vars := mux.Vars(req)
	name := vars["name"]

	r.mu.Lock()
	delete(r.apps, name)
	r.mu.Unlock()

	if err := r.save(); err != nil {
		log.Printf("Error saving data: %v", err)
	}

	w.WriteHeader(http.StatusNoContent)
}

func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, r)
	})
}

func main() {
	dataFile := os.Getenv("DATA_FILE")
	if dataFile == "" {
		dataFile = "/data/apps.json"
	}

	registry := NewRegistry(dataFile)

	router := mux.NewRouter()
	router.Use(corsMiddleware)

	api := router.PathPrefix("/api/v1").Subrouter()
	api.HandleFunc("/apps", registry.ListApps).Methods("GET")
	api.HandleFunc("/apps", registry.CreateApp).Methods("POST")
	api.HandleFunc("/apps/{name}", registry.GetApp).Methods("GET")
	api.HandleFunc("/apps/{name}", registry.DeleteApp).Methods("DELETE")

	router.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	}).Methods("GET")

	log.Println("App Registry API listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", router))
}
