buildLanding();

function buildLanding(){
   var param = getParameter('landing');
   if (param === null) param = 'default';

   var landing = CUSTOMLANDING.find(landing => landing.name === param );

   var titleItem = document.getElementById("title");
   titleItem.innerHTML = landing.title.toString();

   var descriptionItem = document.getElementById("description");
   descriptionItem.innerHTML = landing.description;

   var backgroundImageItem = document.getElementById("promo");
   backgroundImageItem.style.background = "url('" + landing.backgroundImage + "') right 20px top no-repeat";

   var productsText = document.getElementById("productsText");
   productsText.innerHTML = landing.productsText;
    
   var invoiceItem = document.getElementById("invoice");
   if (!landing.products.includes("invoice")) invoiceItem.style.display = "none";
   var invoiceTitle = document.getElementById("invoiceTitle");
   invoiceTitle.innerHTML = landing.invoiceText[0].toString();
   var invoiceDescription = document.getElementById("invoiceDescription");
   invoiceDescription.innerHTML = landing.invoiceText[1].toString();

   var pp3Item = document.getElementById("pp3");
   if (!landing.products.includes("pp3")) pp3Item.style.display = "none";
   var pp3Title = document.getElementById("pp3Title");
   pp3Title.innerHTML = landing.pp3Text[0].toString();
   var pp3Description = document.getElementById("pp3Description");
   pp3Description.innerHTML = landing.pp3Text[1].toString();

   var pp5Item = document.getElementById("pp5");
   if (!landing.products.includes("pp5")) pp5Item.style.display = "none";
   var pp5Title = document.getElementById("pp5Title");
   pp5Title.innerHTML = landing.pp5Text[0].toString();
   var pp5Description = document.getElementById("pp5Description");
   pp5Description.innerHTML = landing.pp5Text[1].toString();
}


function getParameter(name) {
   var result = null,
      tmp = [];
   var items = window.location.search.substr(1).split("&");
   for (var index = 0; index < items.length; index++) {
      tmp = items[index].split("=");
      if (tmp[0] === name) result = decodeURIComponent(tmp[1]);
   }
   return result;
}