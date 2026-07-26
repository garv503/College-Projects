gtype = input("Enter garment type: ")
stype = input("Enter sub type: ")
price = float(input("Enter price: "))
g = 10

if gtype == 'Woolen':   
    if stype == 'sweater':
        d = 12/100*price
    elif stype == 'Jacket':
        d = 8/100*price
    elif stype == 'Blazer':
        d = 10/100*price
        
elif gtype == 'Festive':
    if stype == 'Kurta Set':
        d = 12/100*price
    elif stype == 'Sherwani':
        d = 16/100*price

    elif stype == 'Nehru Jacket':
        d = 8/100*price
amt = price - d
gst = g/100*price
net = amt + gst

print("\t\t\t\tSHIVAM GARMENTS")
print("\t\t\t\tINVOICE")
print("*"*78)
print("Garment Type :\t",gtype)
print("Sub Type     :\t",stype)
print("Price        :\t",price)
print("Discount     :\t",d)
print("-----------------------")
print("Total Amt    :\t",amt)
print("GST          :\t",gst)
print("-----------------------")
print("NET AMOUNT   :\t",net)
print("*"*78)
print("THANKS FOR SHOPPING WITH US")
