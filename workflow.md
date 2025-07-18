# 节点编排系统开发文档

## 概述

本文档旨在指导您实现一个功能强大且灵活的**节点编排系统**，类似于 n8n 或 Dify。该系统将支持**触发器、操作、转换和逻辑节点**，并能无缝集成 **AI Agent** 以实现自主决策和智能工作流。

-----

## 系统设计

### 核心概念

1.  **节点 (Node)**: 工作流中的基本执行单元，负责处理特定任务。
2.  **连接 (Connection)**: 定义节点之间的数据流向和执行顺序。
3.  **工作流 (Workflow)**: 由节点和连接构成的有向图，代表一个完整的业务流程。
4.  **上下文 (Context)**: 节点间传递的数据载体，包含工作流执行过程中的所有相关信息。

### JSON 结构设计

工作流的定义将通过 JSON 结构进行描述，便于存储、传输和解析。

```json
{
  "workflow": {
    "name": "示例工作流",
    "description": "这是一个演示工作流",
    "nodes": [
      {
        "id": "node1",
        "type": "trigger/timer",
        "config": {
          "interval": "5m"
        }
      },
      {
        "id": "node2",
        "type": "action/http",
        "config": {
          "url": "https://api.example.com/data",
          "method": "GET"
        }
      }
    ],
    "connections": [
      {
        "from": "node1",
        "to": "node2",
        "dataMapping": {} // 新增：显式数据映射
      }
    ]
  }
}
```

-----

## 节点类型

### 1\. 触发器节点 (Trigger Nodes)

**功能**: 启动工作流的执行。

**类型**:

  * `timer`: **定时触发**，按预设时间间隔或特定时间点启动。
  * `webhook`: **HTTP 请求触发**，接收外部 HTTP 请求后启动。
  * `manual`: **手动触发**，通过用户界面或 API 调用启动。

**示例配置**:

```json
{
  "id": "trigger1",
  "type": "trigger/timer",
  "config": {
    "interval": "30s",
    "startTime": "2023-01-01T00:00:00Z"
  }
}
```

### 2\. 操作节点 (Action Nodes)

**功能**: 执行具体任务或与外部系统交互。

**类型**:

  * `http`: **HTTP 请求**，发送 HTTP 请求到指定 URL。
  * `db`: **数据库操作**，执行数据库查询、插入、更新等操作。
  * `email`: **发送邮件**，发送电子邮件通知。
  * `ai_agent`: **AI 代理决策**，集成 AI 模型进行智能决策。

**示例配置**:

```json
{
  "id": "action1",
  "type": "action/http",
  "config": {
    "url": "https://api.example.com/users",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json"
    },
    "body": {
      "name": "{{input.name}}",
      "age": "{{input.age}}"
    }
  }
}
```

### 3\. 转换节点 (Transformation Nodes)

**功能**: 对数据进行处理、格式化或校验。

**类型**:

  * `map`: **数据映射**，将输入数据字段映射到新的输出结构。
  * `filter`: **数据过滤**，根据条件筛选数据。
  * `transform`: **格式转换**，例如 JSON 到 XML，或特定数据类型转换。
  * `validate`: **数据校验**，根据预设规则验证数据合法性。

**示例配置**:

```json
{
  "id": "transform1",
  "type": "transform/map",
  "config": {
    "mappings": {
      "output.fullName": "{{input.firstName}} {{input.lastName}}",
      "output.age": "{{input.age}}"
    }
  }
}
```

### 4\. 逻辑节点 (Logic Nodes)

**功能**: 控制工作流的执行流程。

**类型**:

  * `if`: **条件分支**，根据条件真假导向不同分支。
  * `switch`: **多条件分支**，根据表达式值导向多个分支。
  * `loop`: **循环**，对数据集合进行迭代处理。
  * `merge`: **合并**，汇聚多个分支的执行流。

**示例配置**:

```json
{
  "id": "logic1",
  "type": "logic/if",
  "config": {
    "condition": "{{input.value}} > 100",
    "trueNext": "node3",
    "falseNext": "node4"
  }
}
```

-----

## AI Agent 集成

AI Agent 节点能够利用大型语言模型（LLM）分析当前上下文，并根据分析结果决定下一步应执行哪个节点或进行何种操作。

**示例配置**:

```json
{
  "id": "ai1",
  "type": "action/ai_agent",
  "config": {
    "model": "deepseek-chat",
    "prompt": "分析用户输入并决定下一步操作。如果输入包含订单信息，转到订单处理节点；否则转到客服节点。",
    "openai_api_key_ref": "deepseek_api_key", // 引用外部配置，而非硬编码
    "base_url": "https://api.deepseek.com/v1",
    "outputMapping": {
      "nextNodeId": "{{aiDecision}}"
    }
  }
}
```

-----

## 执行引擎设计

执行引擎是工作流系统的核心，负责解析、调度和执行工作流。

1.  **解析器 (Parser)**: 读取并校验 JSON 格式的工作流定义。
2.  **调度器 (Scheduler)**: 决定节点的执行顺序，处理并发和分支逻辑。
3.  **上下文管理器 (Context Manager)**: 管理节点间的数据传递和生命周期，确保数据隔离和可追溯性。
4.  **节点执行器 (Node Executor)**: 封装并执行具体节点的逻辑。

<!-- end list -->


-----

## 完整示例

### 工作流定义

```json
{
  "workflow": {
    "name": "用户注册处理流程",
    "description": "处理新用户注册并发送欢迎邮件",
    "nodes": [
      {
        "id": "trigger",
        "type": "trigger/webhook",
        "config": {
          "path": "/register"
        }
      },
      {
        "id": "validate",
        "type": "transform/validate",
        "config": {
          "rules": {
            "email": "required|email",
            "password": "required|min:8"
          }
        }
      },
      {
        "id": "ai_check",
        "type": "action/ai_agent",
        "config": {
          "model": "gpt-3.5-turbo",
          "prompt": "分析用户注册信息，判断是否是高风险用户。如果是返回{risk: true}，否则{risk: false}",
          "openai_api_key_ref": "openai_api_key",
          "outputMapping": {
            "risk": "{{aiOutput.risk}}"
          }
        }
      },
      {
        "id": "create_user",
        "type": "action/db",
        "config": {
          "operation": "insert",
          "table": "users",
          "data": {
            "email": "{{input.email}}",
            "password": "{{hashedPassword}}"
          }
        }
      },
      {
        "id": "send_email",
        "type": "action/email",
        "config": {
          "to": "{{input.email}}",
          "subject": "欢迎加入我们",
          "body": "感谢您的注册！"
        }
      },
      {
        "id": "review_required",
        "type": "action/http",
        "config": {
          "url": "https://internal.api/review",
          "method": "POST",
          "body": {
            "email": "{{input.email}}",
            "reason": "高风险用户"
          }
        }
      }
    ],
    "connections": [
      {
        "from": "trigger",
        "to": "validate"
      },
      {
        "from": "validate",
        "to": "ai_check"
      },
      {
        "from": "ai_check",
        "to": "create_user",
        "condition": "{{risk}} == false"
      },
      {
        "from": "ai_check",
        "to": "review_required",
        "condition": "{{risk}} == true"
      },
      {
        "from": "create_user",
        "to": "send_email"
      }
    ]
  }
}
```

-----

## 实现建议

1.  **数据结构**: 使用**有向无环图 (DAG)** 来表示工作流，方便进行拓扑排序和依赖分析。
2.  **模板引擎**: 实现一个强大的**上下文模板引擎**来处理 `{{variable}}` 替换，支持表达式求值和条件逻辑。
3.  **错误处理与重试**: 实现节点级的**错误捕获、重试机制**和全局错误处理策略，提高工作流的健壮性。


-----
