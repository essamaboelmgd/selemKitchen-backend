from fastapi import APIRouter, HTTPException, status, Header
from typing import Dict, Any, List
from datetime import datetime, timedelta
from app.database import get_database
from app.services.auth_service import TokenData
import jwt
from app.services.auth_service import SECRET_KEY, ALGORITHM

router = APIRouter()

async def get_current_user_from_token(token: str) -> TokenData:
    """Get current user from token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id, role=role)
    except jwt.PyJWTError:
        raise credentials_exception
    return token_data

@router.get("/stats")
async def get_dashboard_stats(authorization: str = Header(None)):
    """
    جلب إحصائيات لوحة التحكم
    
    Returns:
    - dict: إحصائيات المشاريع، الوحدات، حسابات التقطيع، والتوفير
    """
    try:
        # Extract token from Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        
        token = authorization[len("Bearer "):]
        token_data = await get_current_user_from_token(token)
        
        db = get_database()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Get user's projects count
        projects_count = await db.projects.count_documents({
            "created_by": token_data.user_id
        })
        
        # Get user's units count
        units_cursor = db.units.find({"created_by": token_data.user_id})
        units_count = 0
        cutting_calculations_count = 0
        
        async for unit in units_cursor:
            units_count += 1
            cutting_calculations_count += 1  # Each unit calculation counts as one
        
        # For demo purposes, we'll return static values for some stats
        # In a real application, these would be calculated from actual data
        stats = {
            "projects": projects_count,
            "units": units_count,
            "cutting_calculations": cutting_calculations_count,
            "savings_percentage": 32  # Static value for demo
        }
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving dashboard stats: {str(e)}"
        )

@router.get("/recent-projects")
async def get_recent_projects(limit: int = 3, authorization: str = Header(None)):
    """
    جلب أحدث المشاريع
    
    Parameters:
    - limit: عدد المشاريع المراد جلبها (الافتراضي: 3)
    
    Returns:
    - List[dict]: قائمة بأحدث المشاريع
    """
    try:
        # Extract token from Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        
        token = authorization[len("Bearer "):]
        token_data = await get_current_user_from_token(token)
        
        db = get_database()
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Get recent projects for the user
        projects_cursor = db.projects.find(
            {"created_by": token_data.user_id}
        ).sort("created_at", -1).limit(limit)
        
        recent_projects = []
        async for project_doc in projects_cursor:
            # Count units in project
            units_count = len(project_doc.get("unit_ids", []))
            
            # Calculate how many days ago the project was created
            created_at = project_doc["created_at"]
            days_ago = (datetime.utcnow() - created_at).days
            
            if days_ago == 0:
                date_text = "اليوم"
            elif days_ago == 1:
                date_text = "أمس"
            else:
                date_text = f"منذ {days_ago} أيام"
            
            recent_projects.append({
                "id": project_doc["_id"],
                "name": project_doc["name"],
                "units": units_count,
                "date": date_text
            })
        
        return recent_projects
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving recent projects: {str(e)}"
        )

@router.get("/tip-of-the-day")
async def get_tip_of_the_day(authorization: str = Header(None)):
    """
    جلب نصيحة اليوم
    
    Returns:
    - dict: نصيحة اليوم مع الترجمة
    """
    try:
        # Extract token from Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        
        # Simple tips array - in a real application this could be stored in DB
        tips = [
            {
                "title": "💡 نصيحة اليوم",
                "content": "يمكنك توفير المزيد من المواد عن طريق تعديل إعدادات التقطيع الخاصة بك. جرب تقليل سماكة التراكب الجانبي للحصول على قطع أكثر كفاءة."
            },
            {
                "title": "💡 نصيحة اليوم",
                "content": "استخدم إعدادات التخصيص لتحديد أسعار المواد الخاصة بك للحصول على تقديرات تكلفة دقيقة."
            },
            {
                "title": "💡 نصيحة اليوم",
                "content": "قم بتنظيم مشاريعك في مجلدات لتسهيل عملية البحث والوصول إليها لاحقاً."
            }
        ]
        
        # Return the first tip for now - in a real application this could rotate
        return tips[0]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving tip of the day: {str(e)}"
        )