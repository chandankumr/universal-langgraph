import subprocess
import os
import yaml
import logging
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class DeploymentService:
    """One-click deployment for Vector DBs and services."""
    
    def __init__(self):
        self.base_dir = Path("./deployments")
        self.base_dir.mkdir(exist_ok=True)
    
    def deploy_vector_db(self, db_type: str, user_id: str) -> Dict[str, Any]:
        """Deploy vector DB with one click."""
        
        deployment_dir = self.base_dir / db_type / user_id
        deployment_dir.mkdir(parents=True, exist_ok=True)
        
        if db_type == "chroma":
            return {
                "success": True,
                "message": "Chroma DB runs locally. No deployment needed.",
                "status": "ready"
            }
        
        elif db_type == "qdrant":
            return self._deploy_docker_service(
                db_type,
                deployment_dir,
                image="qdrant/qdrant",
                ports={"6333:6333": 6333},
                volumes={"./qdrant_storage:/qdrant/storage": None}
            )
        
        elif db_type == "weaviate":
            return self._deploy_docker_service(
                db_type,
                deployment_dir,
                image="semitechnologies/weaviate:1.19.0",
                ports={"8080:8080": 8080},
                volumes={"./weaviate_/var/lib/weaviate": None},
                environment={
                    "QUERY_DEFAULTS_LIMIT": "25",
                    "AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED": "true"
                }
            )
        
        elif db_type == "pinecone":
            return {
                "success": False,
                "message": "Pinecone is cloud-only. Please sign up at pinecone.io",
                "status": "external",
                "signup_url": "https://app.pinecone.io/"
            }
        
        else:
            return {
                "success": False,
                "message": f"Automatic deployment not available for {db_type}",
                "status": "manual",
                "docs_url": f"https://{db_type}.io/docs"
            }
    
    def _deploy_docker_service(
        self, 
        db_type: str, 
        deployment_dir: Path,
        image: str,
        ports: dict,
        volumes: dict = None,
        environment: dict = None
    ) -> Dict[str, Any]:
        """Deploy Docker service."""
        
        # Create docker-compose.yml
        compose_config = {
            "version": "3.8",
            "services": {
                db_type: {
                    "image": image,
                    "ports": list(ports.keys()),
                    "restart": "unless-stopped"
                }
            }
        }
        
        if volumes:
            compose_config["services"][db_type]["volumes"] = list(volumes.keys())
        
        if environment:
            compose_config["services"][db_type]["environment"] = environment
        
        compose_file = deployment_dir / "docker-compose.yml"
        with open(compose_file, "w") as f:
            yaml.dump(compose_config, f)
        
        # Start Docker
        try:
            result = subprocess.run(
                ["docker-compose", "up", "-d"],
                cwd=deployment_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": f"{db_type.upper()} deployed successfully",
                    "status": "running",
                    "access_url": f"http://localhost:{list(ports.values())[0]}",
                    "config_file": str(compose_file)
                }
            else:
                return {
                    "success": False,
                    "message": f"Deployment failed: {result.stderr}",
                    "status": "error"
                }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "Deployment timeout",
                "status": "timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "status": "error"
            }
    
    def stop_deployment(self, db_type: str, user_id: str) -> Dict[str, Any]:
        """Stop deployed service."""
        deployment_dir = self.base_dir / db_type / user_id
        compose_file = deployment_dir / "docker-compose.yml"
        
        if not compose_file.exists():
            return {
                "success": False,
                "message": "No deployment found"
            }
        
        try:
            result = subprocess.run(
                ["docker-compose", "down"],
                cwd=deployment_dir,
                capture_output=True,
                text=True
            )
            
            return {
                "success": result.returncode == 0,
                "message": "Service stopped" if result.returncode == 0 else result.stderr
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
    
    def get_deployment_status(self, db_type: str, user_id: str) -> Dict[str, Any]:
        """Check deployment status."""
        deployment_dir = self.base_dir / db_type / user_id
        compose_file = deployment_dir / "docker-compose.yml"
        
        if not compose_file.exists():
            return {
                "deployed": False,
                "status": "not_deployed"
            }
        
        try:
            result = subprocess.run(
                ["docker-compose", "ps"],
                cwd=deployment_dir,
                capture_output=True,
                text=True
            )
            
            is_running = "Up" in result.stdout
            
            return {
                "deployed": True,
                "status": "running" if is_running else "stopped",
                "details": result.stdout
            }
        except Exception as e:
            return {
                "deployed": False,
                "status": "error",
                "error": str(e)
            }

deployment_service = DeploymentService()