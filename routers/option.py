from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db

from moduels.OptionDB import OptionCategory, OptionItem
from Schemas.OptionSchema import OptionCategoryCreate, OptionCategoryResponse, OptionCategoryUpsert

router = APIRouter(prefix="/options", tags=["Options"])


# ✅ POST - Create Category with Options
@router.post("/", response_model=OptionCategoryResponse)
def upsert_category(data: OptionCategoryCreate, db: Session = Depends(get_db)):

    # ✅ If ID is provided → UPDATE
    if data.id:
        category = db.query(OptionCategory).filter(
            OptionCategory.id == data.id
        ).first()

        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        # update key (optional)
        category.key = data.key

    else:
        # ✅ CREATE
        category = OptionCategory(key=data.key)
        db.add(category)
        db.flush()

    # ✅ Existing options
    existing_options = {opt.value: opt for opt in category.options}
    incoming_values = [opt.value for opt in data.options]

    # ✅ UPDATE / ADD
    for opt in data.options:
        if opt.value in existing_options:
            existing = existing_options[opt.value]
            existing.label = opt.label
            existing.symbol = opt.symbol
        else:
            new_item = OptionItem(
                label=opt.label,
                value=opt.value,
                symbol=opt.symbol,
                category_id=category.id
            )
            db.add(new_item)

    # ✅ DELETE removed
    for value, opt in existing_options.items():
        if value not in incoming_values:
            db.delete(opt)

    db.commit()
    db.refresh(category)

    return category


@router.post("/{key}", response_model=OptionCategoryResponse)
def upsert_category(key: str, data: OptionCategoryUpsert, db: Session = Depends(get_db)):
    # ✅ Find category by key
    category = db.query(OptionCategory).filter(
        OptionCategory.key == key
    ).first()

    # ✅ CREATE if not exists
    if not category:
        category = OptionCategory(key=key)
        db.add(category)
        db.flush()

    # ✅ Existing options
    existing_options = {opt.value: opt for opt in category.options}
    incoming_values = [opt.value for opt in data.options]

    # ✅ UPDATE / ADD
    for opt in data.options:
        if opt.value in existing_options:
            existing = existing_options[opt.value]
            existing.label = opt.label
            existing.symbol = opt.symbol
        else:
            new_item = OptionItem(
                label=opt.label,
                value=opt.value,
                symbol=opt.symbol,
                category_id=category.id
            )
            db.add(new_item)

    # ✅ DELETE removed
    for value, opt in existing_options.items():
        if value not in incoming_values:
            db.delete(opt)

    db.commit()
    db.refresh(category)

    # 🔥 VERY IMPORTANT
    return category   # 👈 THIS LINE FIXES YOUR NULL



# ✅ GET - All categories with options
@router.get("/", response_model=list[OptionCategoryResponse])
def get_all(db: Session = Depends(get_db)):
    return db.query(OptionCategory).all()


# ✅ GET - Single category (like gender, currency)
@router.get("/{key}", response_model=OptionCategoryResponse)
def get_by_key(key: str, db: Session = Depends(get_db)):
    category = db.query(OptionCategory).filter(OptionCategory.key == key).first()

    if not category:
        raise HTTPException(status_code=404, detail="Not found")

    return category


@router.post("/id-format")
def update_id_format(entity: str, prefix: str, separator: str, db: Session = Depends(get_db)):
    config = db.query(IdSetting).filter(IdSetting.entity_type == entity).first()
    
    if not config:
        config = IdSetting(entity_type=entity)
        db.add(config)
    
    config.prefix = prefix
    config.separator = separator
    db.commit()
    return {"status": "success", "message": f"{entity} format updated"}