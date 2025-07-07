#!/usr/bin/env python3
"""
Basic usage examples for ARM Edge AI Platform

This script demonstrates how to interact with the platform's services
for embedding generation, similarity search, and analytics.
"""

import requests
import json
import time
from typing import List, Dict, Any

# Service URLs (adjust if running on different host)
EMBEDDINGS_URL = "http://localhost:8001"
ANALYTICS_URL = "http://localhost:8002"
LOG_AGGREGATOR_URL = "http://localhost:8004"
PLOTLY_VIZ_URL = "http://localhost:8003"

def check_service_health():
    """Check if all services are running and healthy"""
    services = {
        "Embeddings": f"{EMBEDDINGS_URL}/health",
        "Analytics": f"{ANALYTICS_URL}/health", 
        "Log Aggregator": f"{LOG_AGGREGATOR_URL}/health",
        "Plotly Viz": PLOTLY_VIZ_URL
    }
    
    print("🔍 Checking service health...")
    for name, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            status = "✅ Healthy" if response.status_code == 200 else f"❌ Error {response.status_code}"
            print(f"  {name}: {status}")
        except requests.exceptions.RequestException as e:
            print(f"  {name}: ❌ Unreachable ({e})")
    print()

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts"""
    print(f"🧠 Generating embeddings for {len(texts)} texts...")
    
    response = requests.post(
        f"{EMBEDDINGS_URL}/embed/batch",
        json={"texts": texts, "normalize": True},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        embeddings = result["embeddings"]
        print(f"  ✅ Generated {len(embeddings)} embeddings (384 dimensions)")
        return embeddings
    else:
        print(f"  ❌ Error: {response.status_code} - {response.text}")
        return []

def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts"""
    print(f"📊 Calculating similarity between texts...")
    
    response = requests.post(
        f"{EMBEDDINGS_URL}/similarity",
        json={"text1": text1, "text2": text2},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        similarity = result["similarity"]
        print(f"  ✅ Similarity: {similarity:.4f}")
        return similarity
    else:
        print(f"  ❌ Error: {response.status_code} - {response.text}")
        return 0.0

def perform_clustering(embeddings: List[List[float]]) -> Dict[str, Any]:
    """Perform clustering analysis on embeddings"""
    print(f"🔬 Performing clustering analysis...")
    
    response = requests.post(
        f"{ANALYTICS_URL}/cluster_analysis",
        json={
            "vectors": embeddings,
            "eps": 0.3,
            "min_samples": 2
        },
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        clusters = result.get("decisions", {}).get("cluster_labels", [])
        n_clusters = len(set(clusters)) if clusters else 0
        print(f"  ✅ Found {n_clusters} clusters")
        return result
    else:
        print(f"  ❌ Error: {response.status_code} - {response.text}")
        return {}

def send_log_data(logs: List[Dict[str, Any]]):
    """Send log data to the log aggregator"""
    print(f"📝 Sending {len(logs)} log entries...")
    
    response = requests.post(
        f"{LOG_AGGREGATOR_URL}/ingest/batch",
        json={"logs": logs},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        print(f"  ✅ Logs successfully processed")
    else:
        print(f"  ❌ Error: {response.status_code} - {response.text}")

def get_log_stats() -> Dict[str, Any]:
    """Get log aggregation statistics"""
    print("📈 Getting log aggregation statistics...")
    
    response = requests.get(f"{LOG_AGGREGATOR_URL}/stats")
    
    if response.status_code == 200:
        stats = response.json()
        print(f"  ✅ Retrieved statistics")
        return stats
    else:
        print(f"  ❌ Error: {response.status_code} - {response.text}")
        return {}

def main():
    """Main demonstration function"""
    print("🚀 ARM Edge AI Platform - Basic Usage Examples")
    print("=" * 50)
    
    # Check service health
    check_service_health()
    
    # Example texts for processing
    sample_texts = [
        "Machine learning algorithms for edge computing",
        "Vector databases and similarity search",
        "ARM processors optimization techniques",
        "Real-time data processing pipelines",
        "Docker containers on Raspberry Pi",
        "PostgreSQL with vector extensions",
        "FastAPI microservices architecture",
        "Node-RED workflow automation"
    ]
    
    # Generate embeddings
    embeddings = generate_embeddings(sample_texts)
    
    if embeddings:
        # Perform clustering
        clustering_result = perform_clustering(embeddings)
        
        # Calculate similarity between first two texts
        if len(sample_texts) >= 2:
            similarity = calculate_similarity(sample_texts[0], sample_texts[1])
    
    # Send sample log data
    sample_logs = [
        {
            "message": "User authentication successful",
            "level": "INFO",
            "source": "auth-service",
            "metadata": {"user_id": "user123", "ip": "192.168.1.100"}
        },
        {
            "message": "Database query completed",
            "level": "DEBUG", 
            "source": "db-service",
            "metadata": {"query_time": "0.05s", "rows": 42}
        },
        {
            "message": "High memory usage detected", 
            "level": "WARN",
            "source": "monitor-service",
            "metadata": {"memory_usage": "85%", "threshold": "80%"}
        }
    ]
    
    send_log_data(sample_logs)
    
    # Get log statistics
    log_stats = get_log_stats()
    if log_stats:
        print(f"  📊 Total logs processed: {log_stats.get('total_logs', 'Unknown')}")
        print(f"  📊 Aggregation ratio: {log_stats.get('aggregation_ratio', 'Unknown')}")
    
    print("\n🎉 Example completed! Visit http://localhost:8003 to see visualizations")
    print("\n💡 Next steps:")
    print("  • View the Plotly dashboard for interactive visualizations")
    print("  • Check the analytics results for clustering insights")
    print("  • Monitor logs for processing statistics")
    print("  • Explore the API documentation at service_url/docs")

if __name__ == "__main__":
    main()