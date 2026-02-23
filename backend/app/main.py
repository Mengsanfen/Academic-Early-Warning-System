"""
FastAPI 应用入口
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db, get_db
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    # 启动时
    print(f"[*] {settings.APP_NAME} 启动中...")
    print(f"[*] API 文档: http://localhost:8000/docs")

    # 初始化数据库表
    init_db()
    print("[OK] 数据库初始化完成")

    yield

    # 关闭时
    print(f"[*] {settings.APP_NAME} 关闭中...")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    description="基于多源数据与规则引擎的学业预警系统",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# ========== 中间件：处理特殊路由 ==========

@app.middleware("http")
async def handle_special_routes(request: Request, call_next):
    """
    处理特殊路由，避免被动态路径参数捕获

    主要解决：/students/classes 被 /students/{student_id} 捕获的问题
    """
    path = request.url.path

    # 检查是否是 /students/classes 或 /students/accessible-classes 路由
    if path in ["/api/v1/students/classes", "/api/v1/students/accessible-classes"]:
        # 从 students_classes 模块导入处理函数
        from app.api.v1.students_classes import router as students_classes_router
        from app.api.deps import get_current_user
        from app.api.v1 import students as students_module

        # 获取当前用户
        try:
            # 手动调用对应的处理函数
            from app.api.v1.students import get_accessible_classes

            # 获取数据库会话
            db = next(get_db())

            # 从请求头获取认证信息
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                from fastapi import HTTPException, status
                return Response(
                    content='{"detail":"未提供认证信息"}',
                    status_code=401,
                    media_type="application/json"
                )

            token = auth_header.split(" ")[1]
            from app.core.security import verify_token
            user_id = verify_token(token)
            if not user_id:
                from fastapi import HTTPException, status
                return Response(
                    content='{"detail":"无效的认证令牌"}',
                    status_code=401,
                    media_type="application/json"
                )

            # 获取用户
            from app.models.user import User
            current_user = db.query(User).filter(User.id == int(user_id)).first()
            if not current_user or not current_user.is_active:
                from fastapi import HTTPException, status
                return Response(
                    content='{"detail":"用户不存在或已被禁用"}',
                    status_code=403,
                    media_type="application/json"
                )

            # 调用处理函数
            result = get_accessible_classes(db=db, current_user=current_user)

            # 返回结果
            import json
            return Response(
                content=json.dumps(result, ensure_ascii=False),
                status_code=200,
                media_type="application/json"
            )

        except Exception as e:
            import json
            return Response(
                content=json.dumps({"detail": str(e)}, ensure_ascii=False),
                status_code=500,
                media_type="application/json"
            )
        finally:
            if 'db' in locals():
                db.close()

    # 继续处理其他请求
    response = await call_next(request)
    return response


# 配置静态文件服务（用于上传的头像等）
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
