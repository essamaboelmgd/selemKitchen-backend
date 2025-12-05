from fastapi import APIRouter, HTTPException, status, Header
from typing import List, Optional
import uuid
from datetime import datetime
from app.models.projects import (
    ProjectCreateRequest, 
    ProjectUpdateRequest, 
    ProjectResponse,
    ProjectDocument
)
from app.models.units import UnitDocument
from app.database import get_database
from app.services.auth_service import TokenData, get_user_by_id, get_user_units_count
import jwt
from app.services.auth_service import SECRET_KEY, ALGORITHM

async def get_current_user(authorization: str = Header(None)) -> Optional[TokenData]:
    """Extract current user from authorization header"""
    if not authorization:
        return None
    
    if not authorization.startswith("Bearer "):
        return None
    
    token = authorization[len("Bearer "):]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None:
            return None
        return TokenData(user_id=user_id, role=role)
    except jwt.PyJWTError:
        return None

router = APIRouter()

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(request: ProjectCreateRequest, authorization: str = Header(None)):
    """
    إنشاء مشروع جديد
    
    Parameters:
    - request: بيانات المشروع (الاسم، الوصف، اسم العميل)
    
    Returns:
    - ProjectResponse: تفاصيل المشروع المنشأ
    """
    try:
        # Extract user from token
        current_user = await get_current_user(authorization)
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        db = get_database()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # إنشاء معرف المشروع
        project_id = f"proj_{uuid.uuid4().hex[:8].upper()}"
        
        # إنشاء مستند المشروع
        project_doc = {
            "_id": project_id,
            "name": request.name,
            "description": request.description or "",
            "client_name": request.client_name or "",
            "unit_ids": [],
            "created_by": current_user.user_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # حفظ المشروع في قاعدة البيانات
        await db.projects.insert_one(project_doc)
        
        return ProjectResponse(
            project_id=project_id,
            name=request.name,
            description=request.description or "",
            client_name=request.client_name or "",
            units=[],
            created_at=project_doc["created_at"],
            updated_at=project_doc["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating project: {str(e)}"
        )

@router.get("/", response_model=List[ProjectResponse])
async def list_projects(authorization: str = Header(None)):
    """
    جلب قائمة بجميع المشاريع
    
    Returns:
    - List[ProjectResponse]: قائمة بجميع المشاريع
    """
    try:
        # Extract user from token
        current_user = await get_current_user(authorization)
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        db = get_database()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # جلب جميع المشاريع للمستخدم الحالي أو جميع المشاريع للمسؤول
        query = {}
        if current_user.role != "admin":
            query["created_by"] = current_user.user_id
            
        projects_cursor = db.projects.find(query)
        projects = []
        
        async for project_doc in projects_cursor:
            # جلب الوحدات المرتبطة بالمشروع
            units = []
            if "unit_ids" in project_doc and project_doc["unit_ids"]:
                units_cursor = db.units.find({"_id": {"$in": project_doc["unit_ids"]}})
                async for unit_doc in units_cursor:
                    # تحويل المستند إلى UnitDocument مع ضمان وجود id
                    unit_data = unit_doc.copy()
                    unit_data["id"] = unit_doc["_id"]
                    units.append(UnitDocument(**unit_data))
            
            projects.append(ProjectResponse(
                project_id=project_doc["_id"],
                name=project_doc["name"],
                description=project_doc.get("description", ""),
                client_name=project_doc.get("client_name", ""),
                units=units,
                created_at=project_doc["created_at"],
                updated_at=project_doc.get("updated_at")
            ))
        
        return projects
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing projects: {str(e)}"
        )

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, authorization: str = Header(None)):
    """
    جلب تفاصيل مشروع معين
    
    Parameters:
    - project_id: معرف المشروع
    
    Returns:
    - ProjectResponse: تفاصيل المشروع
    """
    try:
        # Extract user from token
        current_user = await get_current_user(authorization)
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        db = get_database()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # جلب المشروع
        project_doc = await db.projects.find_one({"_id": project_id})
        
        if project_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with id {project_id} not found"
            )
        
        # التحقق من صلاحيات الوصول للمستخدم العادي
        if current_user.role != "admin" and project_doc.get("created_by") != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this project"
            )
        
        # جلب الوحدات المرتبطة بالمشروع
        units = []
        if "unit_ids" in project_doc and project_doc["unit_ids"]:
            units_cursor = db.units.find({"_id": {"$in": project_doc["unit_ids"]}})
            async for unit_doc in units_cursor:
                # تحويل المستند إلى UnitDocument مع ضمان وجود id
                unit_data = unit_doc.copy()
                unit_data["id"] = unit_doc["_id"]
                units.append(UnitDocument(**unit_data))
        
        return ProjectResponse(
            project_id=project_doc["_id"],
            name=project_doc["name"],
            description=project_doc.get("description", ""),
            client_name=project_doc.get("client_name", ""),
            units=units,
            created_at=project_doc["created_at"],
            updated_at=project_doc.get("updated_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving project: {str(e)}"
        )

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, request: ProjectUpdateRequest, authorization: str = Header(None)):
    """
    تحديث مشروع معين
    
    Parameters:
    - project_id: معرف المشروع
    - request: بيانات التحديث
    
    Returns:
    - ProjectResponse: تفاصيل المشروع المحدث
    """
    try:
        # Extract user from token
        current_user = await get_current_user(authorization)
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        db = get_database()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # التحقق من وجود المشروع
        project_doc = await db.projects.find_one({"_id": project_id})
        
        if project_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with id {project_id} not found"
            )
        
        # التحقق من صلاحيات الوصول للمستخدم العادي
        if current_user.role != "admin" and project_doc.get("created_by") != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this project"
            )
        
        # تحديث البيانات
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.description is not None:
            update_data["description"] = request.description
        if request.client_name is not None:
            update_data["client_name"] = request.client_name
            
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            await db.projects.update_one(
                {"_id": project_id},
                {"$set": update_data}
            )
            
            # تحديث project_doc للحصول على القيم المحدثة
            project_doc.update(update_data)
        
        # جلب الوحدات المرتبطة بالمشروع
        units = []
        if "unit_ids" in project_doc and project_doc["unit_ids"]:
            units_cursor = db.units.find({"_id": {"$in": project_doc["unit_ids"]}})
            async for unit_doc in units_cursor:
                # تحويل المستند إلى UnitDocument مع ضمان وجود id
                unit_data = unit_doc.copy()
                unit_data["id"] = unit_doc["_id"]
                units.append(UnitDocument(**unit_data))
        
        return ProjectResponse(
            project_id=project_doc["_id"],
            name=project_doc["name"],
            description=project_doc.get("description", ""),
            client_name=project_doc.get("client_name", ""),
            units=units,
            created_at=project_doc["created_at"],
            updated_at=project_doc.get("updated_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating project: {str(e)}"
        )

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str, authorization: str = Header(None)):
    """
    حذف مشروع معين
    
    Parameters:
    - project_id: معرف المشروع
    """
    try:
        # Extract user from token
        current_user = await get_current_user(authorization)
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        db = get_database()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # التحقق من وجود المشروع
        project_doc = await db.projects.find_one({"_id": project_id})
        
        if project_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with id {project_id} not found"
            )
        
        # التحقق من صلاحيات الوصول للمستخدم العادي
        if current_user.role != "admin" and project_doc.get("created_by") != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this project"
            )
        
        # حذف الوحدات المرتبطة بالمشروع
        if "unit_ids" in project_doc and project_doc["unit_ids"]:
            await db.units.delete_many({"_id": {"$in": project_doc["unit_ids"]}})
        
        # حذف المشروع
        await db.projects.delete_one({"_id": project_id})
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting project: {str(e)}"
        )

@router.post("/{project_id}/units/{unit_id}")
async def add_unit_to_project(project_id: str, unit_id: str, authorization: str = Header(None)):
    """
    إضافة وحدة إلى مشروع معين
    
    Parameters:
    - project_id: معرف المشروع
    - unit_id: معرف الوحدة
    
    Returns:
    - رسالة تأكيد
    """
    try:
        # Extract user from token
        current_user = await get_current_user(authorization)
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        db = get_database()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # التحقق من وجود المشروع
        project_doc = await db.projects.find_one({"_id": project_id})
        
        if project_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with id {project_id} not found"
            )
        
        # التحقق من صلاحيات الوصول للمستخدم العادي
        if current_user.role != "admin" and project_doc.get("created_by") != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this project"
            )
        
        # التحقق من وجود الوحدة
        unit_doc = await db.units.find_one({"_id": unit_id})
        
        if unit_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unit with id {unit_id} not found"
            )
        
        # Check subscription limits for non-admin users when adding unit to project
        if current_user.role != "admin":
            user = await get_user_by_id(current_user.user_id)
            if user and not user.subscription.is_unlimited_units:
                # Get user's current unit count for the month
                current_units_count = await get_user_units_count(current_user.user_id, 30)
                
                # Check if user has reached their limit
                if current_units_count >= user.subscription.max_units_per_month:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"لقد بلغت الحد الأقصى من الوحدات ({user.subscription.max_units_per_month} وحدة/شهر). يرجى التواصل مع المسؤول لزيادة الحد."
                    )
        
        # التحقق من أن الوحدة ليست مرتبطة بمشروع آخر
        existing_link = await db.projects.find_one({
            "_id": {"$ne": project_id},
            "unit_ids": unit_id
        })
        
        if existing_link:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unit {unit_id} is already linked to another project"
            )
        
        # إضافة الوحدة إلى المشروع
        if unit_id not in project_doc.get("unit_ids", []):
            await db.projects.update_one(
                {"_id": project_id},
                {"$addToSet": {"unit_ids": unit_id}}
            )
        
        return {"message": f"Unit {unit_id} added to project {project_id}"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding unit to project: {str(e)}"
        )

@router.delete("/{project_id}/units/{unit_id}")
async def remove_unit_from_project(project_id: str, unit_id: str, authorization: str = Header(None)):
    """
    إزالة وحدة من مشروع معين
    
    Parameters:
    - project_id: معرف المشروع
    - unit_id: معرف الوحدة
    
    Returns:
    - رسالة تأكيد
    """
    try:
        # Extract user from token
        current_user = await get_current_user(authorization)
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        db = get_database()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # التحقق من وجود المشروع
        project_doc = await db.projects.find_one({"_id": project_id})
        
        if project_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with id {project_id} not found"
            )
        
        # التحقق من صلاحيات الوصول للمستخدم العادي
        if current_user.role != "admin" and project_doc.get("created_by") != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this project"
            )
        
        # التحقق من أن الوحدة مرتبطة بالمشروع
        if unit_id not in project_doc.get("unit_ids", []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unit {unit_id} is not linked to project {project_id}"
            )
        
        # إزالة الوحدة من المشروع
        await db.projects.update_one(
            {"_id": project_id},
            {"$pull": {"unit_ids": unit_id}}
        )
        
        return {"message": f"Unit {unit_id} removed from project {project_id}"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing unit from project: {str(e)}"
        )