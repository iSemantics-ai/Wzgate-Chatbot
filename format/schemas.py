from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Union


class DownPayment(BaseModel):
    value: int = Field(
        ..., description="The initial amount of money paid upfront when purchasing a property. Typically expressed as a percentage of the total price or as an exact amount (e.g., '20% down payment' or '10,000 upfront')"
    )
    amount_percent: Literal['exact_amount', 'percentage'] = Field(
        ..., description="Indicates whether the provided value represents an exact amount of money or a percentage. The available options are: ['exact_amount', 'percentage']."
    )

class PaymentPlan(BaseModel):
    downpayment: Optional[DownPayment] = Field(
    ..., description="The initial amount of money paid upfront when purchasing a property. Typically expressed as a percentage of the total price or as an exact amount (e.g., '20% down payment' or '10,000 upfront')\
        You should return the downpayment value as specified by the user (e.g., don't translate the percentage to a exact amount, or translate the exact amount to a percentage). \
        Default is None"
    )
    monthly_payment: Optional[int] = Field(
    ..., description="The recurring payment made on a monthly basis as part of the installment plan. Default is None"
    )
    installments_years: Optional[int] = Field(
    ..., description="The duration for which the payment plan is structured, expressed in years. Default is None"
    )
    

class PropertyType(BaseModel):
    apartment: bool = Field(
        ..., description="A self-contained housing unit occupying part of a building, typically on a single floor. Apartments share common areas like hallways and amenities with other units."
    )
    villa: bool = Field(
        ..., description="Villa is a luxurious, detached property often situated on a sizable plot, offering privacy and high-end amenities. Villas are associated with upscale living and may include gardens, pools, and multiple living spaces."
    ) 
    house: bool = Field(
        ..., description="House is A standalone residential building designed for single-family occupancy. Houses offer private living spaces and may include yards or gardens."
    ) 
    twin_house: bool = Field(
        ..., description="Twin House is a semi-detached property sharing one common wall with another unit, each with separate entrances and private amenities. Twin houses balance privacy with the cost benefits of shared construction."
    ) 
    townhouse: bool = Field(
        ..., description="Townhouse is a multi-story, single-family home sharing walls with adjacent properties, typically part of a uniform development. Townhouses offer individual entrances and may include small private gardens or garages."
    ) 
    duplex: bool = Field(
        ..., description="A residential building divided into two separate units, either stacked vertically or side by side, each with its own entrance. Duplexes can accommodate extended families."
    ) 
    penthouse: bool = Field(
        ..., description="Penthouse is an exclusive unit located on the top floor of a building, often featuring expansive layouts, high-end finishes, and private terraces with panoramic views. Penthouses represent luxury urban living."
    ) 
    chalet: bool = Field(
        ..., description="Chalet is a wooden dwelling with a sloping roof and overhanging eaves. Chalets are popular as vacation homes, especially in mountainous or lakeside areas."
    ) 
    studio: bool = Field(
        ..., description="Studio is a compact, self-contained living space combining the bedroom, living area, and kitchenette into a single room, with a separate bathroom. Studios are ideal for single occupants or as starter homes."
    ) 
    cabin: bool = Field(
        ..., description="Cabin is a small, rustic house typically constructed from wood, often situated in rural or wilderness settings. Cabins serve as retreats or vacation homes, emphasizing simplicity and nature."
    ) 
    palace: bool = Field(
        ..., description=" Palace is a grand and opulent residence, historically associated with royalty or heads of state, featuring extensive grounds, numerous rooms, and luxurious amenities. Palaces symbolize wealth and power."
    )
    whole_building: bool = Field(
        ..., description="Whole Building is an entire structure available for purchase or lease, which may include multiple residential or commercial units. Acquiring a whole building offers control over all units and common areas."
    ) 
    land: bool = Field(
        ..., description="Land is a parcel of undeveloped property available for various uses, such as construction, agriculture, or investment. Land ownership provides opportunities for development or resource utilization."
    ) 
    office: bool = Field(
        ..., description="Office is a commercial space designated for business activities, including workstations, meeting rooms, and support facilities. Offices are essential for companies to conduct operations and serve clients."
    ) 
    retail: bool = Field(
        ..., description="Retail is a commercial property designed for selling goods or services directly to consumers, such as shops, boutiques, or malls. Retail spaces are strategically located to attract foot traffic and drive sales."
    )
    clinic: bool = Field(
        ..., description="Clinic is a healthcare facility offering outpatient services, including medical consultations, diagnostics, and minor treatments. Clinics provide accessible healthcare without the need for hospital admission."
    )
    pharmacy: bool = Field(
        ..., description="Pharmacy is a retail establishment licensed to dispense prescription medications and sell over-the-counter drugs, health products, and often personal care items. Pharmacies play a crucial role in healthcare delivery."
    )
    

class Location(BaseModel):
    value: str = Field(
        ..., description="The English translation of the property location specified by the user, always returned in English, regardless of the language used by the user."
    )
    compound: bool = Field(
        ..., description="True only if the user explicitly requests a property in a compound. \
            Sometimes the user may refer to a compound as a 'village', 'resort', 'resorts', or 'villages'. \
            Defaults to False."
    )
    
class ForRent(BaseModel):
    rental_frequency: Literal['monthly', 'yearly', 'daily', 'weekly'] = Field(
        ..., description="The frequency of the rental payment. Default is 'monthly'."
    )
    rental_duration: Optional[int] = Field(
        ..., description="The duration of the rental in months, years, days, or weeks. Default is None if the user didn't specify the duration."  
    )
    furnishing_status: Literal["fully_furnished", "basic_furnishing", "semi_furnished"] = Field(
        ...,
        description=(
            "The level of furnishing provided in the unit. "
            "Possible values: "
            "'fully_furnished' indicates the unit includes all necessary furniture and appliances for immediate use; "
            "'basic_furnishing' means the unit has only essential built-in items (e.g., wardrobes and kitchen cabinets) without movable furniture; "
            "'semi_furnished' indicates the unit has some furniture and appliances, but is not fully equipped. Default is 'fully_furnished'."
        )
    )    


class ListingType(BaseModel):
    primary_sale: bool = Field(
        ..., description="Indicates whether the property is a primary sale. \
            Sometimes the user may refer to a primary sale as a 'new' or 'newly built' property. \
            Sometimes refer to primary sale as they want to buy or own a property."
    )
    resale: bool = Field(
        ..., description="Indicates whether the property is a resale."
    )
    for_rent: Optional[ForRent] = Field(
        ..., description="The details of the rental if the property is for rent. Default is None."
    )

class ExtractedJSON(BaseModel):
    about_real_estate: bool = Field(
        ..., description="Indicates whether the user's input is related to real estate."
    )
    property_type: Optional[PropertyType] = Field(
        ..., description="Type of property. Default is None"
    )
    location: Optional[List[Location]] = Field(
        ..., description="Location of the property. Default is None."
    )
    bedrooms: Optional[List[int]] = Field(
        ..., description="Number of bedrooms. Default is None."
    )
    bathrooms: Optional[List[int]] = Field(
        ..., description="Number of bathrooms. Default is None."
    )
    price: Optional[List[int]] = Field(
        ..., description="Property price or the rent price specified by the user. \
            Users may use abbreviations such as 'm' for million (e.g., 5m = 5,000,000) or 'k' for thousand (e.g., 10k = 10,000). \
            Convert these abbreviations into their corresponding numeric values. \
            Don't get tricked by the user's input. \
            Default is None."
    )
    area: Optional[List[int]] = Field(
        ..., description="Area of the property in square meters, and don't assume the area if not specified by the user in a clear way. Default is None if not specified by the user."
    )
    
    
    listing_type: Optional[ListingType] = Field(
        ..., description="The type of listing the user is interested in. \
            Sometimes the user may refer to listing type as they want to rent, buy or own a property, or the property is for sale. \
            Default is None."
    )
    
    garden: Optional[bool] = Field(
        ..., description="Indicates whether the property has a garden [true/false]. Default is None."
    )
    roof_space: Optional[bool] = Field(
        ..., description="Indicates whether the property has roof space [true/false]. Default is None."
    )
    floor: Optional[List[int]] = Field(
        ..., description="Floor number for apartments. Default is None."
    )
    payment_plan: Optional[List[PaymentPlan]] = Field(
        ..., description="Payment plan details. Default is None."
    )
    ready_to_move: Optional[bool] = Field(
        ..., description="Indicates if the property is ready for immediate move-in [true/false]. Default is None."
    )
    delivery_date: Optional[str] = Field(
        ..., description="Delivery date of the property in 'yyyy-mm-dd' format. Default is None."
    )
    finishing: Optional[List[str]] = Field(
        ..., description="Level of finishing. Options include [\"Fully Finished\", \"Semi Finished\", \"Core And Shell\"]. Default is None."
    )
    developer_title: Optional[List[str]] = Field(
        ..., description="Name of the property developer. Default is None."
    )
    # transaction_type: Optional[List[str]] = Field(
    #     ..., description="Indicates whether the unit is sold for the first time by the developer or resold by a previous owner. Options: * primary_sale: first-time sale by the developer, * resale: resold by a previous owner. Default is None."
    # )
    featured: Optional[bool] = Field(
        ..., description="Indicates whether the unit is listed among featured properties on the website [true/false]. Default is None."
    )
    
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    success: bool
    data: Optional[ExtractedJSON]
    error: Optional[str] = None
