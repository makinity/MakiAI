"""
MakiAI — Skill Registry
Dynamic skill discovery, auto-loading, dependency injection, and hot-reloading.

Adapted from OpenJarvis Skill & Tool Architecture.
Allows dropping new *.py skill modules into `skills/` for instant activation.
"""

import importlib
import inspect
import sys
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Type

from skills.base_skill import BaseSkill

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
_LOCK = threading.Lock()


class SkillRegistry:
    """
    Registry for dynamic discovery, instantiation, dependency injection,
    and hot-reloading of MakiAI skills.
    """

    def __init__(self, dependencies: Optional[Dict[str, Any]] = None, skills_dir: Path = SKILLS_DIR):
        self.skills_dir = skills_dir
        self.dependencies: Dict[str, Any] = dependencies or {}
        self._skills: Dict[str, BaseSkill] = {}
        self._skill_classes: Dict[str, Type[BaseSkill]] = {}

    def set_dependencies(self, dependencies: Dict[str, Any]) -> None:
        """Update dependency services and re-inject into active skills."""
        self.dependencies.update(dependencies)

    def discover_and_load(self) -> Dict[str, BaseSkill]:
        """
        Scan skills directory, import all modules, find BaseSkill subclasses,
        and instantiate them with available dependencies.
        """
        with _LOCK:
            if not self.skills_dir.exists():
                print(f"[SkillRegistry] Skills directory not found: {self.skills_dir}")
                return {}

            loaded: Dict[str, BaseSkill] = {}

            # Ensure workspace is in sys.path
            workspace_root = str(self.skills_dir.parent)
            if workspace_root not in sys.path:
                sys.path.insert(0, workspace_root)

            for file_path in sorted(self.skills_dir.glob("*.py")):
                if file_path.name in ("__init__.py", "base_skill.py"):
                    continue

                module_name = f"skills.{file_path.stem}"
                try:
                    if module_name in sys.modules:
                        module = importlib.reload(sys.modules[module_name])
                    else:
                        module = importlib.import_module(module_name)

                    # Find BaseSkill classes in module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            inspect.isclass(attr)
                            and issubclass(attr, BaseSkill)
                            and attr is not BaseSkill
                        ):
                            skill_id = getattr(attr, "SKILL_ID", "") or file_path.stem.replace("_skill", "")
                            instance = self._instantiate_skill(attr)
                            if instance:
                                loaded[skill_id] = instance
                                self._skill_classes[skill_id] = attr

                except Exception as e:
                    print(f"[SkillRegistry] Failed to load skill from {file_path.name}: {e}")

            self._skills = loaded
            print(f"[SkillRegistry] Loaded {len(self._skills)} skills: {list(self._skills.keys())}")
            return self._skills

    def _instantiate_skill(self, skill_cls: Type[BaseSkill]) -> Optional[BaseSkill]:
        """
        Inspect skill __init__ parameters and automatically inject matched dependencies.
        """
        gemini = self.dependencies.get("gemini") or self.dependencies.get("gemini_service")
        context_builder = self.dependencies.get("context_builder")
        kb_reader = self.dependencies.get("kb_reader")
        kb_writer = self.dependencies.get("kb_writer")
        reminder_service = self.dependencies.get("reminder_service") or self.dependencies.get("reminder")
        composio_service = self.dependencies.get("composio_service") or self.dependencies.get("composio")

        try:
            sig = inspect.signature(skill_cls.__init__)
            params = sig.parameters

            has_varargs = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params.values())
            has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())

            # 1. Map known dependencies to explicit named parameters
            kwargs = {}
            for param_name, param in params.items():
                if param_name == "self" or param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                    continue
                elif param_name in ("gemini_service", "gemini"):
                    kwargs[param_name] = gemini
                elif param_name == "context_builder":
                    kwargs[param_name] = context_builder
                elif param_name == "kb_reader":
                    kwargs[param_name] = kb_reader
                elif param_name == "kb_writer":
                    kwargs[param_name] = kb_writer
                elif param_name in ("reminder_service", "reminder"):
                    kwargs[param_name] = reminder_service
                elif param_name in ("composio_service", "composio"):
                    kwargs[param_name] = composio_service
                elif param_name in self.dependencies:
                    kwargs[param_name] = self.dependencies[param_name]

            named_param_count = sum(1 for p in params.values() if p.name != "self" and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD))

            if named_param_count > 0:
                param_names = [p for p in params if p != "self"]
                if len(param_names) >= 4 and param_names[0] in ("gemini_service", "gemini") and param_names[1] == "context_builder":
                    pos_count = min(4, len(param_names))
                    pos_args = [gemini, context_builder, kb_reader, kb_writer][:pos_count]
                    leftover_kwargs = {k: v for k, v in kwargs.items() if k not in param_names[:pos_count]}
                    return skill_cls(*pos_args, **leftover_kwargs)
                return skill_cls(**kwargs)

            # If the class accepts *args or **kwargs, pass standard 4 positional dependencies + extra kwargs
            if has_varargs or has_varkw:
                extra_kwargs = {
                    "reminder_service": reminder_service,
                    "composio_service": composio_service,
                }
                return skill_cls(gemini, context_builder, kb_reader, kb_writer, **extra_kwargs)

            return skill_cls(gemini, context_builder, kb_reader, kb_writer)

        except Exception as e:
            # Fallback to standard BaseSkill init
            try:
                return skill_cls(gemini, context_builder, kb_reader, kb_writer)
            except Exception as e2:
                print(f"[SkillRegistry] Instantiation error for {skill_cls.__name__}: {e} / {e2}")
                return None

    def reload_skills(self) -> Dict[str, BaseSkill]:
        """Hot-reload all skills from disk without application restart."""
        print("[SkillRegistry] Hot-reloading skills...")
        return self.discover_and_load()

    def register_skill(self, skill_instance: BaseSkill) -> None:
        """Register a pre-instantiated skill instance at runtime."""
        with _LOCK:
            skill_id = getattr(skill_instance, "SKILL_ID", "") or skill_instance.__class__.__name__.lower()
            self._skills[skill_id] = skill_instance
            print(f"[SkillRegistry] Programmatically registered skill '{skill_id}'")

    def get_skill(self, skill_id: str) -> Optional[BaseSkill]:
        """Get an active skill instance by ID."""
        return self._skills.get(skill_id)

    def get_all_skills(self) -> Dict[str, BaseSkill]:
        """Return all active skill instances."""
        if not self._skills:
            self.discover_and_load()
        return self._skills

    def get_catalog(self) -> List[Dict[str, Any]]:
        """Return structured metadata catalog for all active skills."""
        catalog = []
        for skill_id, skill in self.get_all_skills().items():
            if hasattr(skill, "schema"):
                catalog.append(skill.schema())
            else:
                catalog.append({
                    "id": skill_id,
                    "name": skill_id.replace("_", " ").title(),
                    "description": skill.__doc__ or "",
                    "triggers": getattr(skill, "TRIGGERS", []),
                })
        return catalog
