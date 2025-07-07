#!/usr/bin/env python3
"""
API Examples for ARM Edge AI Platform

Comprehensive examples showing how to use each service API
for production applications.
"""

import asyncio
import aiohttp
import json
import numpy as np
from typing import List, Dict, Any, Optional

class ARMEdgeAIClient:
    """Client wrapper for ARM Edge AI Platform services"""
    
    def __init__(self, base_url: str = "http://localhost"):
        self.embeddings_url = f"{base_url}:8001"
        self.analytics_url = f"{base_url}:8002"
        self.log_aggregator_url = f"{base_url}:8004"
        self.plotly_url = f"{base_url}:8003"
    
    async def generate_embedding(self, text: str, normalize: bool = True) -> Optional[List[float]]:
        """Generate a single embedding vector"""
        async with aiohttp.ClientSession() as session:
            payload = {"text": text, "normalize": normalize}
            async with session.post(
                f"{self.embeddings_url}/embed/single",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["embedding"]
                return None
    
    async def generate_embeddings_batch(self, texts: List[str], normalize: bool = True) -> Optional[List[List[float]]]:
        """Generate embeddings for multiple texts"""
        async with aiohttp.ClientSession() as session:
            payload = {"texts": texts, "normalize": normalize}
            async with session.post(
                f"{self.embeddings_url}/embed/batch", 
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["embeddings"]
                return None
    
    async def calculate_similarity(self, text1: str, text2: str) -> Optional[float]:
        """Calculate cosine similarity between two texts"""
        async with aiohttp.ClientSession() as session:
            payload = {"text1": text1, "text2": text2}
            async with session.post(
                f"{self.embeddings_url}/similarity",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["similarity"]
                return None
    
    async def perform_vector_clustering(self, vectors: List[List[float]], eps: float = 0.3, min_samples: int = 2) -> Optional[Dict[str, Any]]:
        """Perform DBSCAN clustering on vectors"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "vectors": vectors,
                "eps": eps,
                "min_samples": min_samples
            }
            async with session.post(
                f"{self.analytics_url}/cluster_analysis",
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None
    
    async def analyze_similarity_matrix(self, vectors: List[List[float]]) -> Optional[Dict[str, Any]]:
        """Generate similarity analysis for vector set"""
        async with aiohttp.ClientSession() as session:
            payload = {"vectors": vectors, "method": "cosine"}
            async with session.post(
                f"{self.analytics_url}/similarity_analysis",
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None
    
    async def ingest_logs(self, logs: List[Dict[str, Any]]) -> bool:
        """Send log data for aggregation"""
        async with aiohttp.ClientSession() as session:
            payload = {"logs": logs}
            async with session.post(
                f"{self.log_aggregator_url}/ingest/batch",
                json=payload
            ) as response:
                return response.status == 200
    
    async def get_aggregation_stats(self) -> Optional[Dict[str, Any]]:
        """Get log aggregation statistics"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.log_aggregator_url}/stats") as response:
                if response.status == 200:
                    return await response.json()
                return None

async def document_similarity_example():
    """Example: Document similarity search"""
    print("📄 Document Similarity Search Example")
    print("-" * 40)
    
    client = ARMEdgeAIClient()
    
    # Sample documents
    documents = [
        "ARM processors are designed for energy efficiency",
        "Edge computing brings processing closer to data sources", 
        "Vector databases enable semantic search capabilities",
        "Machine learning models can run on edge devices",
        "PostgreSQL with pgvector supports vector operations",
        "Docker containers provide application isolation",
        "Raspberry Pi is a popular ARM-based single board computer",
        "Real-time analytics require low-latency processing"
    ]
    
    print(f"Processing {len(documents)} documents...")
    
    # Generate embeddings
    embeddings = await client.generate_embeddings_batch(documents)
    if not embeddings:
        print("❌ Failed to generate embeddings")
        return
    
    # Find most similar documents to a query
    query = "ARM-based edge computing solutions"
    query_embedding = await client.generate_embedding(query)
    
    if query_embedding:
        # Calculate similarities manually (for demonstration)
        similarities = []
        for i, doc_embedding in enumerate(embeddings):
            similarity = await client.calculate_similarity(query, documents[i])
            if similarity:
                similarities.append((i, documents[i], similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[2], reverse=True)
        
        print(f"\nQuery: '{query}'")
        print("Most similar documents:")
        for i, (idx, doc, sim) in enumerate(similarities[:3]):
            print(f"  {i+1}. [{sim:.3f}] {doc}")

async def clustering_analysis_example():
    """Example: Text clustering analysis"""
    print("\n🔬 Text Clustering Analysis Example")
    print("-" * 40)
    
    client = ARMEdgeAIClient()
    
    # Sample texts from different categories
    texts = [
        # AI/ML category
        "Neural networks for image recognition",
        "Deep learning model optimization",
        "Machine learning inference on edge",
        
        # Hardware category  
        "ARM Cortex-A78 processor architecture",
        "Raspberry Pi GPIO programming",
        "Edge computing hardware selection",
        
        # Software category
        "Docker container orchestration",
        "Microservices architecture patterns", 
        "API design best practices",
        
        # Database category
        "PostgreSQL performance tuning",
        "Vector database indexing strategies",
        "NoSQL vs SQL for analytics"
    ]
    
    print(f"Clustering {len(texts)} texts...")
    
    # Generate embeddings
    embeddings = await client.generate_embeddings_batch(texts)
    if not embeddings:
        print("❌ Failed to generate embeddings")
        return
    
    # Perform clustering
    clustering_result = await client.perform_vector_clustering(embeddings, eps=0.4, min_samples=2)
    
    if clustering_result:
        cluster_labels = clustering_result.get("decisions", {}).get("cluster_labels", [])
        
        # Group texts by cluster
        clusters = {}
        for i, label in enumerate(cluster_labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(texts[i])
        
        print(f"\nFound {len(clusters)} clusters:")
        for cluster_id, cluster_texts in clusters.items():
            if cluster_id == -1:
                print(f"\n🏷️  Noise points ({len(cluster_texts)} items):")
            else:
                print(f"\n🏷️  Cluster {cluster_id} ({len(cluster_texts)} items):")
            for text in cluster_texts:
                print(f"    • {text}")

async def log_processing_example():
    """Example: Log processing and aggregation"""
    print("\n📝 Log Processing Example")
    print("-" * 40)
    
    client = ARMEdgeAIClient()
    
    # Generate sample log data
    log_data = [
        {
            "message": "User john.doe logged in successfully",
            "level": "INFO",
            "source": "auth-service",
            "metadata": {"user_id": "john.doe", "ip": "192.168.1.101", "session_id": "abc123"}
        },
        {
            "message": "Database connection established",
            "level": "INFO", 
            "source": "db-service",
            "metadata": {"connection_pool": "main", "connections": 5}
        },
        {
            "message": "Cache miss for key user:profile:john.doe",
            "level": "DEBUG",
            "source": "cache-service", 
            "metadata": {"cache_type": "redis", "key": "user:profile:john.doe"}
        },
        {
            "message": "High CPU usage detected: 87%",
            "level": "WARN",
            "source": "monitor-service",
            "metadata": {"cpu_usage": 87, "threshold": 80, "node": "worker-01"}
        },
        {
            "message": "Failed to connect to external API",
            "level": "ERROR",
            "source": "integration-service",
            "metadata": {"api_endpoint": "https://api.example.com", "error_code": "timeout"}
        }
    ]
    
    print(f"Sending {len(log_data)} log entries...")
    
    # Send logs for processing
    success = await client.ingest_logs(log_data)
    
    if success:
        print("✅ Logs successfully sent for processing")
        
        # Wait a moment for processing
        await asyncio.sleep(2)
        
        # Get aggregation statistics
        stats = await client.get_aggregation_stats()
        if stats:
            print("\n📊 Aggregation Statistics:")
            print(f"  • Total logs processed: {stats.get('total_logs', 'Unknown')}")
            print(f"  • Aggregation ratio: {stats.get('aggregation_ratio', 'Unknown')}")
            print(f"  • Processing time: {stats.get('avg_processing_time', 'Unknown')}")
        else:
            print("❌ Could not retrieve statistics")
    else:
        print("❌ Failed to send logs")

async def performance_benchmark():
    """Benchmark platform performance"""
    print("\n⚡ Performance Benchmark")
    print("-" * 40)
    
    client = ARMEdgeAIClient()
    
    # Single embedding benchmark
    start_time = asyncio.get_event_loop().time()
    embedding = await client.generate_embedding("Performance test text")
    single_time = asyncio.get_event_loop().time() - start_time
    
    if embedding:
        print(f"✅ Single embedding: {single_time*1000:.2f}ms")
    
    # Batch embedding benchmark
    test_texts = [f"Test document number {i}" for i in range(50)]
    start_time = asyncio.get_event_loop().time()
    batch_embeddings = await client.generate_embeddings_batch(test_texts)
    batch_time = asyncio.get_event_loop().time() - start_time
    
    if batch_embeddings:
        avg_time = (batch_time / len(test_texts)) * 1000
        print(f"✅ Batch embeddings ({len(test_texts)} texts): {batch_time*1000:.2f}ms total, {avg_time:.2f}ms per text")
    
    # Similarity calculation benchmark
    if embedding and batch_embeddings:
        start_time = asyncio.get_event_loop().time()
        similarity = await client.calculate_similarity("Test text A", "Test text B")
        sim_time = asyncio.get_event_loop().time() - start_time
        
        if similarity is not None:
            print(f"✅ Similarity calculation: {sim_time*1000:.2f}ms")

async def main():
    """Run all examples"""
    print("🚀 ARM Edge AI Platform - API Examples")
    print("=" * 50)
    
    try:
        await document_similarity_example()
        await clustering_analysis_example() 
        await log_processing_example()
        await performance_benchmark()
        
        print(f"\n🎉 All examples completed successfully!")
        print(f"\n💡 Next steps:")
        print(f"  • View visualizations at http://localhost:8003")
        print(f"  • Check API docs at http://localhost:800X/docs")
        print(f"  • Monitor system performance and logs")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("Make sure all services are running and accessible")

if __name__ == "__main__":
    asyncio.run(main())