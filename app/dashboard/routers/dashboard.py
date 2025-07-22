from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, date, timedelta
from app.database import get_db
from app.appraisals.models.appraisals import VehicleAppraisal
from app.security.utils import get_current_user
from app.security.models.users import User

router = APIRouter()

# 1. Resumen general
@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = date.today()
    first_day_month = today.replace(day=1)
    first_day_last_month = (first_day_month - timedelta(days=1)).replace(day=1)
    last_day_last_month = first_day_month - timedelta(days=1)

    # Total avalúos este mes
    total_avaluos = db.query(func.count(VehicleAppraisal.vehicle_appraisal_id))\
        .filter(VehicleAppraisal.appraisal_date >= first_day_month).scalar() or 0
    # Total avalúos mes anterior
    total_avaluos_last = db.query(func.count(VehicleAppraisal.vehicle_appraisal_id))\
        .filter(VehicleAppraisal.appraisal_date >= first_day_last_month)\
        .filter(VehicleAppraisal.appraisal_date <= last_day_last_month).scalar() or 0
    # Variación
    if total_avaluos_last:
        var = ((total_avaluos - total_avaluos_last) / total_avaluos_last) * 100
        total_avaluos_variation = f"{var:+.0f}%"
    else:
        total_avaluos_variation = "0%"

    # Ingresos totales (suma appraisal_value_usd)
    total_ingresos = db.query(func.coalesce(func.sum(VehicleAppraisal.appraisal_value_usd), 0))\
        .filter(VehicleAppraisal.appraisal_date >= first_day_month).scalar() or 0
    total_ingresos_last = db.query(func.coalesce(func.sum(VehicleAppraisal.appraisal_value_usd), 0))\
        .filter(VehicleAppraisal.appraisal_date >= first_day_last_month)\
        .filter(VehicleAppraisal.appraisal_date <= last_day_last_month).scalar() or 0
    if total_ingresos_last:
        var = ((total_ingresos - total_ingresos_last) / total_ingresos_last) * 100
        total_ingresos_variation = f"{var:+.0f}%"
    else:
        total_ingresos_variation = "0%"

    # Clientes nuevos (por applicant único)
    clientes_nuevos = db.query(func.count(func.distinct(VehicleAppraisal.applicant)))\
        .filter(VehicleAppraisal.appraisal_date >= first_day_month).scalar() or 0
    clientes_nuevos_last = db.query(func.count(func.distinct(VehicleAppraisal.applicant)))\
        .filter(VehicleAppraisal.appraisal_date >= first_day_last_month)\
        .filter(VehicleAppraisal.appraisal_date <= last_day_last_month).scalar() or 0
    if clientes_nuevos_last:
        var = ((clientes_nuevos - clientes_nuevos_last) / clientes_nuevos_last) * 100
        clientes_nuevos_variation = f"{var:+.0f}%"
    else:
        clientes_nuevos_variation = "0%"

    return {
        "total_avaluos": total_avaluos,
        "total_avaluos_variation": total_avaluos_variation,
        "total_ingresos": int(total_ingresos),
        "total_ingresos_variation": total_ingresos_variation,
        "clientes_nuevos": clientes_nuevos,
        "clientes_nuevos_variation": clientes_nuevos_variation
    }

# 2. Ventas del día (últimos 7 días agrupados por día de la semana)
@router.get("/ventas-dia")
def dashboard_ventas_dia(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    dias = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    max_weeks_back = 12  # Limita la búsqueda a 12 semanas atrás
    week_offset = 0

    while week_offset < max_weeks_back:
        today = date.today() - timedelta(weeks=week_offset)
        # Encuentra el lunes de la semana correspondiente
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        ventas = db.query(
            extract('dow', VehicleAppraisal.appraisal_date).label('dow'),
            func.coalesce(func.sum(VehicleAppraisal.appraisal_value_usd), 0)
        ).filter(
            VehicleAppraisal.appraisal_date >= week_start,
            VehicleAppraisal.appraisal_date <= week_end
        ).group_by('dow').all()

        valores = [0]*7
        for dow, total in ventas:
            idx = int(dow) - 1 if int(dow) > 0 else 6  # PostgreSQL: 0=Domingo
            valores[idx] = float(total)

        if any(valores):  # Si hay al menos un valor distinto de 0, devuelve esa semana
            return {
                "labels": dias,
                "values": valores,
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat()
            }

        week_offset += 1

    # Si no encuentra ninguna semana con datos, devuelve ceros y la semana actual
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    return {
        "labels": dias,
        "values": [0]*7,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat()
    }

# 3. Ventas mensuales (año actual)
@router.get("/ventas-mes")
def dashboard_ventas_mes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    year = date.today().year
    ventas = db.query(
        extract('month', VehicleAppraisal.appraisal_date).label('mes'),
        func.coalesce(func.sum(VehicleAppraisal.appraisal_value_usd), 0)
    ).filter(
        extract('year', VehicleAppraisal.appraisal_date) == year
    ).group_by('mes').all()
    meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    valores = [0]*12
    for mes, total in ventas:
        idx = int(mes)-1
        valores[idx] = float(total)
    return {"labels": meses, "values": valores}

# 4. Carros con más avalúos (top 5)
@router.get("/carros-mas-avaluos")
def dashboard_carros_mas_avaluos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from calendar import monthrange
    max_months_back = 12
    month_offset = 0
    today = date.today()

    while month_offset < max_months_back:
        # Calcular mes y año a consultar
        year = today.year
        month = today.month - month_offset
        while month <= 0:
            month += 12
            year -= 1
        # Primer y último día del mes
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])

        top = db.query(
            VehicleAppraisal.brand,
            func.count(VehicleAppraisal.vehicle_appraisal_id).label('cantidad')
        ).filter(
            VehicleAppraisal.appraisal_date >= first_day,
            VehicleAppraisal.appraisal_date <= last_day
        ).group_by(VehicleAppraisal.brand)
        top = top.order_by(func.count(VehicleAppraisal.vehicle_appraisal_id).desc()).limit(5).all()

        if top:
            labels = [x[0] or "" for x in top]
            values = [x[1] for x in top]
            return {
                "labels": labels,
                "values": values,
                "month": month,
                "year": year
            }
        month_offset += 1

    # Si no hay datos en los últimos 12 meses, devuelve vacío y el mes actual
    return {
        "labels": [],
        "values": [],
        "month": today.month,
        "year": today.year
    } 