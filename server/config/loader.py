"""설정 파일 로더"""
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger
import re


class ConfigLoader:
    """YAML 설정 로더"""
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path("config")
        self._cache: Dict[str, Any] = {}
        self.load_all()
        
    def load_all(self):
        """모든 설정 파일 로드"""
        # 모델 설정
        self._cache["models"] = self._load_yaml("models/endpoints.yml")
        
        # 프롬프트 설정
        prompts_dir = self.config_dir / "prompts"
        if prompts_dir.exists():
            self._cache["prompts"] = {}
            for prompt_file in prompts_dir.glob("*.yml"):
                key = prompt_file.stem
                self._cache["prompts"][key] = self._load_yaml(f"prompts/{prompt_file.name}")
                
        # A/B 테스트 설정
        ab_config = self.config_dir / "ab" / "experiments.yml"
        if ab_config.exists():
            self._cache["ab"] = self._load_yaml("ab/experiments.yml")
            
        logger.info(f"설정 로드 완료: {list(self._cache.keys())}")
        
    def _load_yaml(self, path: str) -> Dict[str, Any]:
        """YAML 파일 로드 및 환경변수 치환"""
        full_path = self.config_dir / path
        if not full_path.exists():
            logger.warning(f"설정 파일 없음: {full_path}")
            return {}
            
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # 환경변수 치환 ${VAR_NAME}
        def replace_env(match):
            var_name = match.group(1)
            value = os.getenv(var_name, "")
            if not value:
                logger.warning(f"환경변수 없음: {var_name}")
            return value
            
        content = re.sub(r'\$\{([^}]+)\}', replace_env, content)
        
        try:
            return yaml.safe_load(content) or {}
        except yaml.YAMLError as e:
            logger.error(f"YAML 파싱 오류 {path}: {e}")
            return {}
            
    def get_model_config(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """모델 설정 반환"""
        models_config = self._cache.get("models", {})
        
        if not provider:
            provider = models_config.get("default", "openai")
            
        providers = models_config.get("providers", {})
        if provider not in providers:
            logger.error(f"프로바이더 없음: {provider}")
            return {}
            
        return providers[provider]
        
    def get_pipeline_mode(self) -> str:
        """파이프라인 모드 반환"""
        models_config = self._cache.get("models", {})
        pipeline = models_config.get("pipeline", {})
        return pipeline.get("mode", "two_call")
        
    def get_prompt(self, key: str) -> str:
        """프롬프트 반환"""
        prompts = self._cache.get("prompts", {})
        
        # key를 점으로 분리 (예: core.persona.ko -> core/persona/ko)
        parts = key.split(".")
        
        # 여러 형태로 시도
        for i in range(len(parts)):
            test_key = ".".join(parts[:i+1])
            if test_key in prompts:
                prompt_data = prompts[test_key]
                if isinstance(prompt_data, dict):
                    return prompt_data.get("system", "")
                return str(prompt_data)
                
        logger.warning(f"프롬프트 없음: {key}")
        return ""
        
    def get_all_prompts(self) -> Dict[str, str]:
        """모든 프롬프트 반환"""
        result = {}
        prompts = self._cache.get("prompts", {})
        
        for key, value in prompts.items():
            if isinstance(value, dict):
                result[key] = value.get("system", "")
            else:
                result[key] = str(value)
                
        return result
        
    def reload(self):
        """설정 다시 로드"""
        self._cache.clear()
        self.load_all()
        
        
# 싱글톤 인스턴스
config_loader = ConfigLoader()
