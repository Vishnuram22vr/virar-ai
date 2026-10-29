import time
import operator
from typing import Dict, Any, Literal
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolExecutionResult, registry

class CalculatorInput(BaseModel):
    operation: Literal["add", "subtract", "multiply", "divide", "power"] = Field(
        ..., description="The mathematical operation to perform"
    )
    a: float = Field(..., description="First operand")
    b: float = Field(..., description="Second operand")

class CalculatorTool(BaseTool):
    name = "calculator"
    description = "Performs deterministic mathematical operations (add, subtract, multiply, divide, power) with strict bounds."
    schema_model = CalculatorInput
    requires_approval = False
    permission_level = "read"

    async def execute(self, params: Dict[str, Any]) -> ToolExecutionResult:
        start_time = time.perf_counter()
        validated = self.schema_model(**params)
        
        try:
            if validated.operation == "add":
                res = validated.a + validated.b
            elif validated.operation == "subtract":
                res = validated.a - validated.b
            elif validated.operation == "multiply":
                res = validated.a * validated.b
            elif validated.operation == "divide":
                if validated.b == 0:
                    return ToolExecutionResult(
                        success=False,
                        error="Division by zero is mathematically undefined.",
                        error_category="validation_error",
                        duration_ms=(time.perf_counter() - start_time) * 1000
                    )
                res = validated.a / validated.b
            elif validated.operation == "power":
                if abs(validated.b) > 100:
                    return ToolExecutionResult(
                        success=False,
                        error="Exponent too large (maximum exponent limit is 100).",
                        error_category="validation_error",
                        duration_ms=(time.perf_counter() - start_time) * 1000
                    )
                res = validated.a ** validated.b
            else:
                return ToolExecutionResult(
                    success=False,
                    error=f"Unsupported operation: {validated.operation}",
                    error_category="validation_error",
                    duration_ms=(time.perf_counter() - start_time) * 1000
                )
            
            return ToolExecutionResult(
                success=True,
                data={"result": res, "operation": validated.operation, "a": validated.a, "b": validated.b},
                duration_ms=(time.perf_counter() - start_time) * 1000
            )
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=str(e),
                error_category="runtime_error",
                duration_ms=(time.perf_counter() - start_time) * 1000
            )

class ServiceHealthInput(BaseModel):
    service_name: str = Field(..., description="The name of the service to inspect (e.g. auth-service, payment-gateway, database-primary)")
    check_type: Literal["ping", "deep", "metrics"] = Field("ping", description="Type of health check")

class ServiceHealthLookupTool(BaseTool):
    name = "service_health_lookup"
    description = "Queries simulated infrastructure and microservice health status, latency, and uptime."
    schema_model = ServiceHealthInput
    requires_approval = False
    permission_level = "read"

    async def execute(self, params: Dict[str, Any]) -> ToolExecutionResult:
        start_time = time.perf_counter()
        validated = self.schema_model(**params)
        
        # Deterministic simulation catalogue
        service_statuses = {
            "auth-service": {"status": "healthy", "latency_ms": 14.2, "uptime": "99.98%"},
            "payment-gateway": {"status": "degraded", "latency_ms": 420.5, "uptime": "98.50%", "warning": "High latency on payment downstream provider"},
            "database-primary": {"status": "healthy", "latency_ms": 2.1, "uptime": "99.99%"},
            "ai-inference-cluster": {"status": "healthy", "latency_ms": 85.0, "uptime": "99.95%"},
            "failing-service": {"status": "outage", "latency_ms": 0.0, "uptime": "92.00%", "error": "Connection refused on port 5432"}
        }

        service_data = service_statuses.get(
            validated.service_name.lower(),
            {"status": "unknown", "latency_ms": 0.0, "uptime": "unknown", "message": f"Service '{validated.service_name}' not found in registry"}
        )
        
        is_success = service_data.get("status") != "outage"
        
        return ToolExecutionResult(
            success=is_success,
            data={
                "service": validated.service_name,
                "check_type": validated.check_type,
                **service_data
            },
            error=service_data.get("error") if not is_success else None,
            error_category="service_outage" if not is_success else None,
            duration_ms=(time.perf_counter() - start_time) * 1000
        )

class IncidentCreationInput(BaseModel):
    title: str = Field(..., min_length=5, max_length=150, description="Brief summary of the incident")
    severity: Literal["low", "medium", "high", "critical"] = Field(..., description="Impact severity")
    target_service: str = Field(..., description="Affected infrastructure or service name")
    description: str = Field(..., min_length=10, description="Detailed diagnosis and reason for incident")

class IncidentCreationTool(BaseTool):
    name = "create_incident_ticket"
    description = "Creates a production incident ticket in the simulated escalation system. PROTECTED ACTION: Requires human approval before execution."
    schema_model = IncidentCreationInput
    requires_approval = True # HUMAN APPROVAL REQUIRED
    permission_level = "admin"

    async def execute(self, params: Dict[str, Any]) -> ToolExecutionResult:
        start_time = time.perf_counter()
        validated = self.schema_model(**params)
        
        # Simulated production ticket response
        ticket_id = f"INC-{int(time.time()) % 100000:05d}"
        
        return ToolExecutionResult(
            success=True,
            data={
                "ticket_id": ticket_id,
                "title": validated.title,
                "severity": validated.severity,
                "target_service": validated.target_service,
                "description": validated.description,
                "status": "created",
                "assigned_team": "SRE-OnCall",
                "message": f"Incident ticket {ticket_id} created successfully after governance sign-off."
            },
            duration_ms=(time.perf_counter() - start_time) * 1000
        )

def register_default_tools():
    for tool_cls in [CalculatorTool, ServiceHealthLookupTool, IncidentCreationTool]:
        tool = tool_cls()
        if tool.name not in registry.list_tools():
            registry.register(tool)

# Register on import
register_default_tools()
