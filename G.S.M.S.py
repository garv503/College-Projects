import pandas as pd
from datetime import date,datetime
import matplotlib.pyplot as plt
print()
dfcustomer = pd.read_csv("Customer Details.csv", index_col = "Cust_ID")
dfbilling  = pd.read_csv("Billing Details.csv",  index_col = "Bill_Id")
dfstock    = pd.read_csv("Stock Details.csv",    index_col = "Stock_Id", encoding = 'latin1')
dfloginid  = pd.read_csv("Login Id.csv",         index_col = "Login_ID")
print('''
**********************************************************************************************************************

                     █████╗ ██████╗ ██████╗  █████╗ ██████╗ ███████╗██╗       ███████╗ █████╗  ██████╗██╗   ██╗
                    ██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔════╝██║       ██╔════╝██╔══██╗██╔════╝╚██╗ ██╔╝
                    ███████║██████╔╝██████╔╝███████║██████╔╝█████╗  ██║       █████╗  ███████║╚█████╗  ╚████╔╝ 
                    ██╔══██║██╔═══╝ ██╔═══╝ ██╔══██║██╔══██╗██╔══╝  ██║       ██╔══╝  ██╔══██║ ╚═══██╗  ╚██╔╝  
                    ██║  ██║██║     ██║     ██║  ██║██║  ██║███████╗███████╗  ███████╗██║  ██║██████╔╝   ██║   
                    ╚═╝  ╚═╝╚═╝     ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝  ╚══════╝╚═╝  ╚═╝╚═════╝    ╚═╝   

                 ██╗       ██╗███████╗██╗      █████╗  █████╗ ███╗   ███╗███████╗ ██████╗  ██╗   ██╗ █████╗ ██╗   ██╗
                 ██║  ██╗  ██║██╔════╝██║     ██╔══██╗██╔══██╗████╗ ████║██╔════╝██╔════╝  ╚██╗ ██╔╝██╔══██╗██║   ██║
                 ╚██╗████╗██╔╝█████╗  ██║     ██║  ╚═╝██║  ██║██╔████╔██║█████╗  ╚█████╗    ╚████╔╝ ██║  ██║██║   ██║
                  ████╔═████║ ██╔══╝  ██║     ██║  ██╗██║  ██║██║╚██╔╝██║██╔══╝   ╚═══██╗    ╚██╔╝  ██║  ██║██║   ██║
                  ╚██╔╝ ╚██╔╝ ███████╗███████╗╚█████╔╝╚█████╔╝██║ ╚═╝ ██║███████╗██████╔╝     ██║   ╚█████╔╝╚██████╔╝
                   ╚═╝   ╚═╝  ╚══════╝╚══════╝ ╚════╝  ╚════╝ ╚═╝     ╚═╝╚══════╝╚═════╝      ╚═╝    ╚════╝  ╚═════╝ 
***********************************************************************************************************************''')                                                                                                                                                                                                                                                                                                                     
while True:
    print()
    print('1. Login\n2. Exit: ')
    a = int(input('Enter Choice: '))
    print()
    if a == 1:
        lid = input('Enter login ID: ')
        password = int(input('Enter Password: '))
        print()
        if lid in dfloginid.index:
            n = dfloginid.loc[lid, 'Password']
            if password == n:
                print('''𝑾𝒆𝒍𝒄𝒐𝒎𝒆 𝑻𝒐 𝑨𝒅𝒎𝒊𝒏 𝑴𝒆𝒏𝒖...''')
                while True:
                    print('''
 █▀▄▀█  █▀▀▀  █▄  █  █  █ 
 █ █ █  █▀▀▀  █ █ █  █  █ 
 █   █  █▄▄▄  █  ▀█  ▀▄▄▀***************************************************
                          * 1. Add                                         *
                          * 2. REMOVE                                      *
                          * 3. MODIFY                                      *
                          * 4. SORT                                        *
                          * 5. SEARCHING                                   *
                          * 6. REPORTS                                     *
                          * 7. DATA VISUALIZATION                          *
                          * 8. LOGOUT                                      *                                        
                          **************************************************''')
                    
                    b = int(input('Enter ur choice: '))
                    if b == 1: #ADDING A RECORD 
                        print('''
                              
 █████╗ ██████╗ ██████╗ 
██╔══██╗██╔══██╗██╔══██╗
███████║██║  ██║██║  ██║
██╔══██║██║  ██║██║  ██║
██║  ██║██████╔╝██████╔╝
╚═╝  ╚═╝╚═════╝ ╚═════╝ ''')

                        print('''
                            ****𝓐𝓓𝓓 𝓣𝓞****************
                            * 1. Customer Details    *
                            * 2. Stock Details       *
                            * 3. Bill Details        *
                            **************************''')
                        c = int(input('Enter ur choice: '))
                        if c == 1:      #ADD A CUSTOMER RECORD
                             print('**********ADDING A NEW CUSTOMER*********')
                             a = dfcustomer.index.max()
                             f = 'A'+ str(int(a[1:])+1).zfill(3)
                             if f in dfcustomer.index:
                                 print("Customer ID Already Exits")
                                 print()
                                 input("Press Enter to continue...")
                             else:
                                Cust_Name = input("Enter the Customer Name: ")
                                Gender = input("Enter the gender of the customer: ")
                                Phn_No = int(input("Enter the Phone Number: "))
                                Email_Id = input("Enter the email id of customer: ")
                                DOB = input("Enter the Date of Birth: ")
                                Address = input("Enter the Address: ")
                                Pin_Code = int(input("Enter the pin code: "))
                                dfcustomer.loc[f] = [Cust_Name,Gender,Phn_No,Email_Id,DOB,Address,Pin_Code]
                                dfcustomer.to_csv('Customer Details.csv')
                                print()
                                print('New Customer Details Added Sucessfully!!!')
                                input("Press Enter to Continue...")

                        elif c == 2:     #ADD A STOCK RECORD
                            print('**********ADDING A NEW STOCK RECORD**********')
                            print('What do you want to add\n1. STOCK FROM NEW VENDOR\n2. ADD A NEW QUANTITY')
                            s = int(input("Enter ur choice: "))
                            if s == 1:        # ADD A STOCK FROM NEW VENDOR
                                a = dfstock.index[-1]
                                b = list(a)
                                b.remove('S')
                                c = ''
                                for i in b:
                                    c = c+i
                                d = int(c)
                                if len(str(d)) == 2:
                                    e = d+1
                                    f = 'S0'+str(e)
                                else:
                                    e = d+1
                                    f = 'S'+str(e)
                                if f in dfstock.index:
                                     print("Stock Id Already Exists!")
                                     input("Press Enter To Continue...")
                                else:
                                    Garment_Name = input("Enter the Garment Name: ")
                                    Vendor_Name = input("Enter the Vendor Name: ")
                                    Qty_Purchased = int(input("Enter the Qty: "))
                                    Unit_Price = float(input("Enter the Unit Price: "))
                                    Description = input("Enter the Description of the Garment: ")
                                    Garment_Type = input("Enter the Garment Type: ")
                                    GST = 10
                                    amt = Qty_Purchased * Unit_Price
                                    net_amt = amt + GST/100*amt
                                    Total_Price = net_amt 
                                    dfstock.loc[f] = [Garment_Name,Vendor_Name,Qty_Purchased,Unit_Price,Description,Garment_Type,GST,Total_Price]
                                    dfstock.to_csv("Stock Details.csv")
                                    print()
                                    print("Stock Deatils Successfuly Added!!!")
                                    print()
                                    input("Press Enter to Continue...")

                            elif s == 2:          #ADD A NEW QUANTITY OF THE EXISTING STOCK
                                print(dfstock.Garment_Name)
                                f = input("Enter the Stock Id of  the Qty Purchased: ")
                                if f in dfstock.index:
                                    print('Additional Purchase')
                                    print()
                                    b = int(input('Enter additional Quantity purchased: '))
                                    qty = int(dfstock.loc[f,'Qty_Purchased'])
                                    unitprice = int(dfstock.loc[f,'Unit_Price'])
                                    tot_qty = qty + b
                                    net = tot_qty * unitprice
                                    g = 10
                                    net_amt = net + g/100*net 
                                    payable_amt = net_amt
                                    dfstock.loc[f,'Qty_Purchased'] = tot_qty
                                    dfstock.loc[f,'Total_Price'] = payable_amt
                                    dfstock.to_csv('Stock Details.csv')
                                    print('Quantity modified Successfully.')
                                    print()
                                    input("Pres Enter to continue...")


                                
                        elif c == 3:     #ADD A BILL RECORD
                            print('**********ADDING A NEW BILL RECORD**********')
                            while True:
                                print(dfcustomer.Cust_Name)
                                print()
                                print(dfstock.Garment_Name)
                                print()
                                a = dfbilling.index.max()
                                billid = 'B' + str(int(a[1:])+1).zfill(3)
                                print()
                                if billid in dfbilling.index:
                                    print('Bill Id Already Exits!')
                                    print()
                                    input("Press Enter to continue...")
                                else:
                                    dfbilling.reset_index(inplace = True)
                                    Cust_Id = input("Enter the customer id: ")
                                    today = date.today()
                                    Bill_Date = today.strftime('%d/%m/%Y')
                                    ctime = datetime.now()
                                    Bill_Time = ctime.strftime('%H:%M:%S')
                                    Mode_of_Trans = input("Enter the Mode of Transaction: ")
                                    addStock = True
                                    while addStock == True:
                                        while True:
                                            Stock_Id = input("Enter the stock id: ")
                                            if Stock_Id in dfstock.index:
                                                dfbillstock = dfstock.loc[[Stock_Id]]
                                                break
                                            else:
                                                print('Invalid Stock Id!')
                                                
                                        Garment_Name = dfbillstock.loc[Stock_Id,'Garment_Name']
                                        Qty_Purchased = int(input("Enter the qty purchased: "))
                                        while Qty_Purchased > int(dfbillstock.iloc[0]['Qty_Purchased']):
                                            print('Insufficient Stock. Enter the new Quantity')
                                            print()
                                            Qty_Purchased = int(input("Enter the Qty: "))
                                            print()
                                        a = int(dfstock.loc[Stock_Id]['Qty_Purchased'])
                                        Q_L = a - Qty_Purchased
                                        dfstock.loc[Stock_Id,'Qty_PUrchased'] = Q_L
                                        dfstock.to_csv('Stock Details.csv')
                                        Unit_Price = int(dfbillstock.Unit_Price)
                                        tot = (Qty_Purchased * Unit_Price)
                                        D = 15
                                        Discount = D/100 * tot
                                        tot = tot - Discount
                                        G = 10
                                        GST = 10/100 * tot
                                        Tot_Pay_Amt = tot + GST

                                        dfbilling.loc[len(dfbilling)] = [billid,Cust_Id,Bill_Date, Bill_Time,Stock_Id,Garment_Name,Qty_Purchased,Unit_Price,D,G,Tot_Pay_Amt,Mode_of_Trans]

                                        print()
                                        anymore = input("Do you want to buy more item? Y/N: ")
                                        if anymore not in 'Yy':
                                            addStock = False

                                    # all items added. Append to dfbilling
                                    dfbilling.set_index('Bill_Id', inplace = True)
                                    dfbilling.to_csv('Billing Details.csv')
                                    print()
                                    print('Bill Details Added Successfully!!!')
                                    print()
                                    input("PRess Enter to continue...")
                                    print()

                                    print('Generating the Bill...') # PRINTING THE BILL OF THE CUSTOMER
                                    print()
                                    bill = dfbilling.loc[[billid]]
                                    print()
                                    print("\t\t\t\tAPPAREL EASY")
                                    print("*"*78)
                                    print("\t\t\t\tINVOICE")
                                    print("*"*78)
                                    bid = bill.index[0]
                                    cid = bill.iloc[0]['Cust_ID']
                                    bdate = bill.iloc[0]['Bill_Date']
                                    btime = bill.iloc[0]['Bill_Time']
                                    mode = bill.iloc[0]['Mode_of_Trans']

                                    print("Bill Id:         :",bid, '\t\t',"Customer Id  :\t",cid)
                                    print("Date and Time:   :",bdate,btime)
                                    print("Payment Mode:    :",mode)
                                    print("*"*78)
                                    tot_pay_amt=0
                                    print("StockID Garment Name        Unit Price Quantity Discount GST Total")
                                    print("*"*78)
                                    for index, data in bill.iterrows():
                                            
                                        sid = data['Stock_Id']
                                        gname = data['Garment_Name']
                                        qty = data['Qty_Sold']
                                        uprice = data['Unit_Price']
                                        d = data['Discount']
                                        g = data['GST']
                                        tot = data['Tot_Pay_Amt']


                                        net = qty * uprice
                                        dprice = d/100*net
                                        netamt = net - dprice
                                        gprice = g/100*netamt
                                        tot_pay_amt += (netamt + gprice)

                                        print(sid,"{:<20}".format(gname),uprice,qty,d,g,tot,sep='\t')
                                    print("_"*75)
                                    print("NET AMOUNT   :\t",tot_pay_amt)
                                    print("*"*78)
                                    print("THANKS FOR SHOPPING WITH US")
                                    print()
                                    input("Press Enter to continue...")

                                break
                                                
                            
                                
                    elif b == 2:     #REMOVING THE DETAILS
                        print('''
                              
██████╗ ███████╗███╗   ███╗ █████╗ ██╗   ██╗███████╗
██╔══██╗██╔════╝████╗ ████║██╔══██╗██║   ██║██╔════╝
██████╔╝█████╗  ██╔████╔██║██║  ██║╚██╗ ██╔╝█████╗  
██╔══██╗██╔══╝  ██║╚██╔╝██║██║  ██║ ╚████╔╝ ██╔══╝  
██║  ██║███████╗██║ ╚═╝ ██║╚█████╔╝  ╚██╔╝  ███████╗
╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝ ╚════╝    ╚═╝   ╚══════╝''')

                        print('''
                            ****𝓡𝓔𝓜𝓞𝓥𝓔 𝓕𝓡𝓞𝓜***************                   
                            * 1. Customer Details       *
                            * 2. Bill Details           *
                            * 3. Stock Details          *
                            *****************************''')
                        c = int(input("Enter ur Choice: "))
                        if c == 1:#REMOVE CUSTOMER DETAILS
                            print("**********REMOVE CUSTOMER DETAILS**********")
                            print(dfcustomer.Cust_Name)
                            e = input("ARE U SURE U WANT TO REMOVE THE DETAILS? (y/n): ")
                            print()
                            if e == 'y' or e == 'Y':
                                while True:
                                    cd = input("Enter the Customer Id to Remove: ")
                                    if cd in dfcustomer.index:
                                        ans = input("Do You Really Want to Remove This Record?(y/n): ")
                                        print()
                                        if ans == 'y' or ans == 'Y':
                                            dfcustomer.drop(cd, axis = 0, inplace = True)
                                            print()
                                            dfcustomer.to_csv("Customer Details.csv")
                                            print("Details Remove Successfully!!!")
                                            print()
                                            input("Press Enter to continue...")
                                        elif ans == 'n' or ans == 'N':
                                            print('Operation Un - Successfull!!!')
                                            print()
                                            input("Press Enter to continue...")
                                            
                                        else:
                                            print('Customer Id Not Found!!!')
                                            print()
                                            input("Press Enter to Continue...")
                                    else:
                                        print('Customer Id not Found!!!')
                                        print()
                                        input("Press Enter to continue...")
                                    break
                            elif e == 'n' or e == 'N':
                                 print('Dont Want to delete the record!')
                                 print()
                                 input("Press Enter to continue...")
                                 
                            else:
                                print('Invalid Choice!')
                                print()
                                input("Press Enter to continue...")
                                
                                   
                        elif c == 2:      #REMOVE BILL DETAILS
                            print('**********REMOVING BILL DETAILS**********')
                            print(dfbilling.index)
                            e = input("ARE U SURE U WANT TO REMOVE THE DETAILS? (y/n): ")
                            print()
                            if e == 'y' or e == 'Y':
                                while True:
                                    bd = input("Enter the Bill Id to Remove: ")
                                    print()
                                    if bd in dfbilling.index:
                                        ans = input("Do You Really Want to Remove This Record?(y/n): ")
                                        print()
                                        if ans == 'y' or ans == 'Y':
                                            dfbilling.drop(bd, axis = 0, inplace = True)
                                            dfbilling.to_csv("Billing Details.csv")
                                            print("Details Remove Successfully!!!")
                                            print()
                                            input("Press Enter to continue...")
                                            
                                        elif ans == 'n' or ans == "N":
                                            print("Operation Un-Successfull!!!")
                                            print()
                                            input("Press Enter to Continue...")
                                        else:
                                           print("Invalid Choice!")
                                           print()
                                           input("Press Enter to Continue...")
                                    else:
                                        print("Bill Id Not Found!!!")
                                        print()
                                        input("Press Enter to Continue...")
                                    break
                            elif e == 'n' or e == 'N':
                                print("DON'T WANT TO DELETE THIS RECORD")
                                print()
                                input("Press Enter to continue...")
                                   
                        elif c == 3:     #REMOVE STOCK DETAILS
                            print('**********REMOVING STOCK DETAILS**********')
                            print(dfstock.Garment_Name)
                            e = input("ARE U SURE U WANT TO REMOVE THE DETAILS? (y/n): ")
                            if e == 'y' or e == 'Y':
                                while True:
                                    sd = input("Enter the Stock Id to Remove: ")
                                    if sd in dfstock.index:
                                        ans = input("Do You Really Want to Remove This Record?(y/n): ")
                                        if ans == 'y' or ans == 'Y':
                                            dfstock.drop(sd, axis = 0, inplace = True)
                                            print()
                                            dfstock.to_csv("Stock Details.csv")
                                            print("Details Remove Successfully!!!")
                                            print()
                                            input("Press Enter to continue...")
                                            
                                        elif ans == 'n' or ans == "N":
                                            print("Operation Un-Successfull!!!")
                                            print()
                                            input("Press Enter to Continue...")
                                        else:
                                           print("Invalid Choice!")
                                           print()
                                           input("Press Enter to Continue...")
                                    else:
                                        print("Bill Id Not Found!!!")
                                        print()
                                        input("Press Enter to Continue...")
                                    break
                            elif e == 'n' or e == 'N':
                                print("DON'T WANT TO DELETE THIS RECORD")
                                print()
                                input("Press Enter to continue...")
                                
                    elif b == 3:              #MODIFICATION
                        print('''
                              
███╗   ███╗ █████╗ ██████╗ ██╗███████╗██╗   ██╗
████╗ ████║██╔══██╗██╔══██╗██║██╔════╝╚██╗ ██╔╝
██╔████╔██║██║  ██║██║  ██║██║█████╗   ╚████╔╝ 
██║╚██╔╝██║██║  ██║██║  ██║██║██╔══╝    ╚██╔╝  
██║ ╚═╝ ██║╚█████╔╝██████╔╝██║██║        ██║   
╚═╝     ╚═╝ ╚════╝ ╚═════╝ ╚═╝╚═╝        ╚═╝   ''')
                        
                        print('''
                        *****𝓜𝓞𝓓𝓘𝓕𝓨 𝓣𝓗𝓡𝓞𝓤𝓖𝓗********
                        * 1. CUSTOMER             *
                        * 2. STOCK                *
                        ***************************''')
                        c = int(input("Enter ur Choice: "))
                        if c == 1:             #MODIFY THROUGH CUSTOMER DETAILS
                            print('''
                          *******𝓜𝓞𝓓𝓘𝓕𝓨 𝓒𝓤𝓢𝓣𝓞𝓜𝓔𝓡 𝓑𝓨***************
                          * 1. Customer Name                    *
                          * 2. Phone Number                     *
                          ***************************************''')
                            d = int(input("Enter ur Choice: "))
                            if d == 1:    #MODIFIED THROUGH CUSTOMER NAME
                                print(dfcustomer.Cust_Name)
                                a = input("Enter the Customer Name to be Modified: ")
                                f = input("Enter the customer Id: ")
                                if a in dfcustomer.Cust_Name.values:
                                    g = input("Enter the New Customer Name: ")
                                    dfcustomer.loc[f,'Cust_Name'] = g
                                    dfcustomer.to_csv('Customer Details.csv')
                                    print("Customer Name Modified!!!")
                                    input("Press Enter to Continue...")
                                else:
                                    print("Customer Name not Found!")
                                    input('Press Enter to Continue...')
                                          
                            elif d == 2:     #MODIFIED THROUGH PHONE NUMBER
                                print()
                                print(dfcustomer[['Cust_Name','Phn_No']])
                                print()
                                c = int(input("Enter the Phone Number to be Modified: "))
                                f = input("Enter the Customer Id of this Phone Number: ")
                                if c in dfcustomer.Phn_No.values:
                                    i = input("Enter the New Phone Number: ")
                                    dfcustomer.loc[f,'Phn_No']=i 
                                    dfcustomer.to_csv('Customer Details.csv')
                                    print("Phone Number Modified!!!")
                                    input("Press Enter to Continue...")
                                else:
                                    print("Phone Number not Found!")
                                    input('Press Enter to Continue...')

                        elif c == 2:     # MODIFICATION OF STOCK DETAILS 
                            print(dfstock.Garment_Name)
                            s = input("Enter the Stock id: ")
                            if s in dfstock.index:
                                print()
                                b = int(input("Enter the qty: "))
                                unit_price = int(dfstock.loc[s,'Unit_Price'])
                                netamt = b * unit_price
                                g = 10
                                tot_amt = netamt + g/100*netamt
                                dfstock.loc[s,'Qty_Purchased'] = b
                                dfstock.loc[s,'Total_Price'] = tot_amt
                                dfstock.to_csv("Stock Details.csv")
                                print()
                                print("Qty Modified!!!")
                                print()
                                input("Press Enter to continue...")
                                print()
                                
                                    

                    elif b == 4:          #SORTING A RECORD
                            
                            print('''
                                  
 ██████╗ █████╗ ██████╗ ████████╗
██╔════╝██╔══██╗██╔══██╗╚══██╔══╝
╚█████╗ ██║  ██║██████╔╝   ██║   
 ╚═══██╗██║  ██║██╔══██╗   ██║   
██████╔╝╚█████╔╝██║  ██║   ██║   
╚═════╝  ╚════╝ ╚═╝  ╚═╝   ╚═╝   ''')
                            print('''
                            *****𝓢𝓞𝓡𝓣 𝓑𝓨********
                            * 1. CUSTOMER     *
                            * 2. BILL         *
                            * 3. STOCK        *
                            *******************''')
                            c = int(input("Enter ur Choice: "))
                            if c == 1:       #SORTING CUSTOMER DETAILS
                                print('''
                                ***𝑺𝑶𝑹𝑻 𝑪𝑼𝑺𝑻𝑶𝑴𝑬𝑹 𝑩𝒀***********                           
                                * 1. CUSTOMER ID          *
                                * 2. CUSTOMER NAME        *
                                * 3. PIN CODE             *
                                ***************************''')
                                d = int(input("Enter ur Choice: "))
                                if d == 1:  #SORTING THE CUSTOMER ID
                                    print('1. SORT THE CUSTOMER ID IN ASCENDING ORDER\n2. SORT THE CUSTOMER ID IN DESCENDING ORDER')
                                    e = int(input("Enter ur Choice: "))
                                    if e == 1:      #SORTING THE CUSTOMER ID IN ASCENDING ORDER
                                        print(dfcustomer.sort_values(by = 'Cust_ID', axis = 0, ascending = True, inplace = False))
                                        f = input('Do You Want To Export Saved Changes? (y/n): ')
                                        if f == 'y' or f == 'Y':
                                            dfcustomer.sort_values(by = 'Cust_ID', axis = 0, ascending = True, inplace = True)
                                            dfcustomer.to_csv('Customer Details.csv')
                                            print('Changes Saved!!!')
                                            
                                            input('Press Enter to Continue...')
                                        elif f == 'n' or f == 'N':
                                            print('Changes Not Saved!')
                                            
                                            input('Press Enter to Continue...')
                                        else:
                                            print('Invalid Choice')
                                            
                                            input('Press Enter to Continue...')
                                    elif e == 2:     #SORTING THE CUSTOMER ID IN DESCENDING ORDER
                                        
                                       print(dfcustomer.sort_values(by = 'Cust_ID', axis = 0, ascending = False, inplace = False))
                                       f = input('Do You Want To Export Saved Changes? (y/n): ')
                                       if f == 'y' or f == 'Y':
                                           dfcustomer.sort_values(by = 'Cust_ID', axis = 0, ascending = False, inplace = True)
                                           dfcustomer.to_csv('Customer Details.csv')
                                           print('Changes Saved!!!')
                                           
                                           input('Press Enter to Continue...')
                                       elif f == 'n' or f == 'N':
                                           print('Changes Not Saved!')
                                           
                                           input('Press Enter to Continue...')
                                       else:
                                           print('Invalid Choice')
                                           
                                           input('Press Enter to Continue...')
                                           
                                elif d == 2:    #SORTING CUSTOMER NAME
                                  print('1. SORT THE CUSTOMER NAME IN ASCENDING ORDER\n2. SORT THE CUSTOMER NAME IN DESCENDING ORDER')
                                  e = int(input("Enter ur Choice: "))
                                  if e == 1:    #SORTING THE NAME IN ASCENDING ORDER:
                                      print(dfcustomer.sort_values(by = 'Cust_Name', axis = 0, ascending = True, inplace = False))
                                      f = input("Do You Want to Export the  Saved the Changes? (y/n): ")
                                      if f == 'y' or f == 'Y':
                                          dfcustomer.sort_values(by = 'Cust_Name', axis = 0, ascending = True, inplace = True)
                                          dfcustomer.to_csv('Customer Details.csv')
                                          print('Changes Sucessfully Exported!')

                                          input('Press Enter to Continue...')
                                      elif f == 'n' or f == 'N':
                                          print('Changes Not Saved!')

                                          input('Press Enter to Continue...')
                                      else:
                                          print('Invalid Choice!')

                                          input('Press Enter to Continue...')
                                  elif e == 2:     #SORTING THE CUSTOMER NAME IN DESCENDING ORDER
                                      print(dfcustomer.sort_values(by = 'Cust_Name', axis = 0, ascending = False, inplace = False))
                                      f = input('Do you Want to Export the Saved Changes? (y/n): ')
                                      if f == 'y' or "Y":
                                          dfcustomer.sort_values(by = 'Cust_Name', axis = 0, ascending = False, inplace = True)
                                          dfcustomer.to_csv('Customer Details.csv')
                                          print('Changes Successfully Exported!')

                                          input('Press Enter to Continue...')
                                      elif f == 'n' or "N":
                                          print('Saved Changes Not Exported!')

                                          input("Press Enter to Continues...")
                                      else:
                                          print('Invalid Choice!')

                                          input('Press Enter to Continue...')
                                          
                                elif d == 3:         #SORTING THE PIN CODE
                                    print('1. SORT PIN CODE IN ASCENDING ORDER\n2. SORT PIN CODE IN DESCENDING ORDER')
                                    d = int(input("Enter ur Choice: "))
                                    if d == 1:#SORTING PIN CODE IN ASCENDING ORDER
                                        print(dfcustomer.sort_values(by = 'Pin_Code', axis = 0, ascending = True, inplace = False))
                                        f = input("Do You Want to Export the Saved Changes? (y/n): ")
                                        if f == 'y' or f == 'Y':
                                            dfcustomer.sort_values(by = 'Pin_Code', axis = 0, ascending = True, inplace = True)
                                            dfcustomer.to_csv('Customer Details.csv')
                                            print("Saved Changes Exported Successfully!!!")
                                            input("Press Enter to Continue...")
                                        elif f == 'n' or f == 'N' :
                                            print('Saved Changes Not Exported!')
                                            input("Press Enter To COntinue...")
                                        else:
                                            print('Invalid Choice!')
                                            input("Press Enter to Continue")
                                    elif d == 2:   #SORTING PIN CODE IN DESCENDING ORDER
                                        print(dfcustomer.sort_values(by = 'Pin_Code', axis = 0, ascending = False, inplace = False))
                                        f = input("DO YOU WANT TO EXPORT THE SAVE CHANGES? (y/n): ")
                                        if f == 'y' or f ==  'Y':
                                            dfcustomer.sort_values(by = 'Pin_Code', axis = 0, ascending = False, inplace = True)
                                            dfcustomer.to_csv('Customer Details.csv')
                                            print("Saved Changes Exported Successfully!!!")
                                            input("Press Enter to Continue...")
                                        elif f == 'n' or f == 'N':
                                            print("Saved Changes Not Exported!")
                                            input("Press Enter to Continue...")
                                        else:
                                            print("Invalid Choice!")
                                            input("Press Enter to Continue...")
    
                            
                            elif c == 2:    #SORTING BILL DETAILS
                                print('''
                                *****𝓢𝓞𝓡𝓣 𝓑𝓘𝓛𝓛 𝓑𝓨**********
                                * 1. BILL ID            *
                                * 2. CUSTOMER ID        *
                                * 3. QTY SOLD           *
                                *************************''')
                                d = int(input("Enter ur Choice: "))
                                if d ==1:     #SORTING THE BILL ID
                                    print('1. SORT BILL ID IN ASCENDING ORDER\n2. SORT BILL ID IN DESCENDING ORDER')
                                    e = int(input("Enter ur Choice: "))
                                    if e == 1:   #SORING BILL ID IN ASCENDING ORDER
                                        print(dfbilling.sort_values(by = 'Bill_Id', axis = 0, ascending = True, inplace = False))
                                        f = input("DO YOU WANT TO EXPORT THE SAVE CHANGES? (y/n): ")
                                        if f == 'y' or f == 'Y':
                                            dfbilling.sort_values(by = 'Bill_Id', axis = 0, ascending = True, inplace = True)
                                            dfbilling.to_csv('Billing Details.csv')
                                            print("Saved Changes Succesfully Exported!!!")
                                            input("Press Enter to Continue...")
                                        elif f == 'n' or 'N':
                                            print("Saved Chnages Not Exported!")
                                            input("Press Enter To Continue...")
                                        else:
                                            print('Invalid Choice!')
                                            input("Press Enter to Continue...")
                                    elif e == 2:    #SORTING THE BILL ID IN DESCENDING ORDER
                                        print(dfbilling.sort_values(by = 'Bill_Id', axis = 0, ascending = False, inplace = False))
                                        f = input("DO YOU WANT TO EXPORT THE SAVE CHANGES? (y/n): ")
                                        if f == 'y' or f == 'Y':
                                            dfbilling.sort_values(by = 'Bill_Id', axis = 0, ascending = False, inplace = True)
                                            dfbilling.to_csv('Billing Details.csv')
                                            print("Saved Changes Succesfully Exported!!!")

                                            input("Press Enter to Continue...")
                                        elif f == 'n' or 'N':
                                            print("Saved Chnages Not Exported!")

                                            input("Press Enter To Continue...")
                                        else:
                                            print('Invalid Choice!')

                                elif d == 2:  #SORTING THE CUSTOMER ID (BILLING DETAILS)
                                    print('1. SORT THE CUST ID IN ASCENDING ORDER\n2. SORT THE CUST ID IN DESCENDING ORDER')
                                    e = int(input("Enter ur Choice: "))
                                    if e == 1:  #SORTING THE CUSTOMER ID (BILING DETAILS) IN ASCENDING ORDER
                                        print(dfbilling.sort_values(by = 'Cust_ID', axis = 0, ascending = True, inplace = False))
                                        f = input("DO YOU WANT TO EXPORT THE SAVE CHANGES? (y/n): ")
                                        if f == 'y' or f == 'Y':
                                            dfbilling.sort_values(by = 'Cust_ID', axis = 0, ascending = True, inplace = True)
                                            dfbilling.to_csv('Billing Details.csv')
                                            print("Saved Changes Succesfully Exported!!!")

                                            input("Press Enter to Continue...")
                                        elif f == 'n' or 'N':
                                            print("Saved Chnages Not Exported!")

                                            input("Press Enter To Continue...")
                                        else:
                                            print('Invalid Choice!')
                                    elif e ==2:    #SORTING THE CUSTOMER ID (BILLING DETAILS) IN DESCENDING ORDER
                                        print(dfbilling.sort_values(by = 'Cust_ID', axis = 0, ascending = False, inplace = False))
                                        f = input("DO YOU WANT TO EXPORT THE SAVE CHANGES? (y/n): ")
                                        if f == 'y' or f == 'Y':
                                            dfbilling.sort_values(by = 'Cust_ID', axis = 0, ascending = False, inplace = True)
                                            dfbilling.to_csv('Billing Details.csv')
                                            print("Saved Changes Succesfully Exported!!!")

                                            input("Press Enter to Continue...")
                                        elif f == 'n' or 'N':
                                            print("Saved Chnages Not Exported!")

                                            input("Press Enter To Continue...")
                                        else:
                                            print('Invalid Choice!')

                                elif d == 3:    #SORTING QTY SOLD
                                    print('1. SORT THE QTY SOLD IN ASCENDING ORDER\n2. SORT THE QTY PURCHASE IN DESCENDING ORDER')
                                    e = int(input("Enter ur Choice: "))
                                    if e == 1:     #SORTING QTY SOLD IN ASCENDING ORDER
                                        print(dfbilling.sort_values(by = 'Qty_Sold', axis = 0, ascending = True, inplace = False))
                                        f = input("DO YOU WANT TO EXPORT THE SAVE CHANGES? (y/n): ")
                                        if f == 'y' or f == 'Y':
                                            dfbilling.sort_values(by = 'Qty_Sold', axis = 0, ascending = True, inplace = True)
                                            dfbilling.to_csv('Billing Details.csv')
                                            print("Saved Changes Succesfully Exported!!!")

                                            input("Press Enter to Continue...")
                                        elif f == 'n' or 'N':
                                            print("Saved Chnages Not Exported!")

                                            input("Press Enter To Continue...")
                                        else:
                                            print('Invalid Choice!')
                                    elif e == 2:  #SORTING QTY SOLD IN DESCENDING ORDER
                                        print(dfbilling.sort_values(by = 'Qty_Sold', axis = 0, ascending = False, inplace = False))
                                        f = input("DO YOU WANT TO EXPORT THE SAVE CHANGES? (y/n): ")
                                        if f == 'y' or f == 'Y':
                                            dfbilling.sort_values(by = 'Qty_Sold', axis = 0, ascending = False, inplace = True)
                                            dfbilling.to_csv('Billing Details.csv')
                                            print("Saved Changes Succesfully Exported!!!")

                                            input("Press Enter To Continue...")
                                        elif f == 'n' or 'N':
                                            print("Saved Chnages Not Exported!")

                                            input("Press Enter To Continue...")
                                        else:
                                            print('Invalid Choice!')

                            elif c == 3:     #SORTING STOCK 
                                    print('''
                                    *****𝓢𝓞𝓡𝓣 𝓢𝓣𝓞𝓒𝓚 𝓑𝓨********
                                    * 1. STOCK ID           * 
                                    * 2. GARMENT TYPE       *
                                    * 3. QTY                *
                                    * 4. UNIT PRICE         *
                                    *************************''')
                                    d = int(input("Enter ur Choice: "))
                                    if d == 1:    #SORTING STOCK ID
                                        print('1. SORT STOCK ID IN ASCENDING ORDER\n2. SORT STOCK ID IN DESCENDING ORDER')
                                        e = int(input("Enter ur Choice: "))
                                        if e == 1:    #SORTING STOCK ID IN ASCENDING ORDER
                                            print(dfstock.sort_values(by = 'Stock_Id', axis = 0, ascending = True, inplace = False))
                                            f = input("DO YOU WANT TO EXPORT THE SAVE CHANGES? (y/n): ")
                                            if f == 'y' or f == 'Y':
                                                dfstock.sort_values(by = 'Stock_Id', axis = 0, ascending = True, inplace = True)
                                                dfstock.to_csv("Stock Details.csv")
                                                print("Saved Changes Exported Successfully!!!")

                                                input("Press Enter to Continue...")
                                            elif f == 'n' or 'N':
                                                print("Saved Changes Not Exported!")

                                                input("Press Enter to Continue...")
                                            else:
                                                print('Invalid Choice!')

                                                input("Press Enter to Continue...")
                                        elif e == 2:   #SORTING STOCK ID IN DESCENDING ORDER
                                           print(dfstock.sort_values(by = 'Stock_Id',axis = 0, ascending = False, inplace = False))
                                           f = input("DO YOU WANT TO EXPORT THE SAVED CHANGES? (y/n): ")
                                           if f == 'y'or f == 'Y':
                                               dfstock.sort_values(by = 'Stock_Id',axis = 0, ascending = False, inplace = True)
                                               dfstock.to_csv("Stock Details.csv")
                                               print("Saved Changes Exported Successfully!!!")

                                               input("Press Enter to Continue...")
                                           elif f == 'n' or f == 'N':
                                                print("Saved Changes Not Exported!")

                                                input("Press Enter to Continue...")
                                           else:
                                                print('Invalid Choice!')

                                                input("Press Enter to Continue...")

                                    elif d == 2:    #SORTING THE GARMENT TYPE
                                        print('1. SORT THE GARMENT TYPE IN ASCEN.\n2. SORT THE GARMENT TYPE IN DESCEN.')
                                        e = int(input("Enter ur Choice: "))
                                        if e == 1:  #SORTING GARMENT TYPE IN ASCENDING ORDER
                                            print(dfstock.sort_values(by = "Garment_Type",axis = 0, ascending = True, inplace = False))
                                            f = input("DO YOU WANT TO EXPORT THE SAVE CHANGES? (y/n): ")
                                            if f == 'y' or f == 'Y':
                                                dfstock.sort_values(by = 'Garment_Type',axis = 0, ascending = True, inplace = True)
                                                dfstock.to_csv('Stock Details.csv')
                                                print('Saved Changes Exported Successfully!!!')

                                                input("Press Enter to Continue...")
                                            elif f == 'n' or 'N':
                                                print('Saved Changes Not Exported!')

                                                input("Press Enter to Continue...")
                                            else:
                                                print('Invalid Choice!')

                                                input("Press Enter to Continue...")
                                        elif e == 2:      #SORTING GARMENT TYPE IN DESCENDING ORDER
                                            print(dfstock.sort_values(by = 'Garment_Type', axis = 0, ascending = False, inplace = False))
                                            f = input('DO YOU WANT TO EXPORT THE SAVED CHANGES?(y/n): ')
                                            if f == 'y' or f == 'Y':
                                                dfstock.sort_values(by = 'Garment_Type',axis = 0, ascending = False, inplace = True)
                                                dfstock.to_csv("Stock Details.csv")
                                                print('Saved Changes Exported Successfully!!!')

                                                input("Press Enter to Continue...")
                                            elif f == 'n' or f == 'N':
                                                print("Saved Changes Not Exported!")

                                                input("Press Enter to Continue...")
                                            else:
                                                print('Invalid Choice!')

                                                input('Press Enter to Continue')

                                    elif d == 3:     #SORTING QTY 
                                        print('1. SORT THE QTY IN ASCEN.\n2. SORT THE QTY  IN DESCEN.')
                                        e = int(input("Enter ur Choice: "))
                                        if e == 1:     #SORTING QTY  IN ASCENDING ORDER
                                            print(dfstock.sort_values(by = 'Qty_Purchased',axis = 0,ascending = True,inplace = False))
                                            f = input("DO YOU WANT TO EXPORT THE SAVE CHANGES? (y/n): ")
                                            if f == 'y' or f == 'Y':
                                                dfstock(by = 'Qty_Purchased', axis = 0, ascending = True, inplace = True)
                                                dfstock.to_csv('Stock Details.csv')
                                                print('Saved Changes Exported Successfully!!!')

                                                input('Press Enter to Continue...')
                                            elif f == 'n' or f == 'N':
                                                print('Saved Changes Not Exported!')

                                                input("Press Enter to Continue...")
                                            else:
                                                print('Invalid Choice!')
                                        elif e == 2:     #SORTING QTY  IN DESCENDING ORDER
                                            print(dfstock.sort_values(by = 'Qty_Purchased', axis = 0, ascending = False, inplace = False))
                                            f = input("DO YOU WANT TO EXPORT THE SAVE CHANGES? (y/n): ")
                                            if f == 'y' or f == 'Y':
                                                dfstock.sort_values(by = 'Qty_Purchased',axis = 0, ascending = False, inplace = True)
                                                dfstock.to_csv('Stock Details.csv')
                                                print('Saved Changes Exported Successfully!!!')
                                                print()
                                                input('Press Enter to Continue...')
                                                
                                            elif f == 'n' or f == 'N':
                                                print('Saved Changes Not Exported!')
                                                print()
                                                input('Press Enter to Continue...')
                                            else:
                                                print('Invalid Choice!')
                                                print()
                                                input('Press Enter to Continue...')
                                                print()

                                    elif d == 4:    # SORTING BY TOTAL PRICE
                                        print('1. SORT UNIT PRICE IN ASCEN.\n2. SORT UNIT PRICE IN DESC.')
                                        e = int(input("Enter ur choice: "))
                                        if e == 1:        # SORTING THE TOTAL PRICE IN ASCENDING ORDER
                                            print(dfstock.sort_values(by = 'Unit_Price',axis = 0, ascending = True, inplace = False))
                                            f = input('DO YOU WANT TO EXPORT THE SAVE CHANGES? (y/n): ')
                                            if f == 'y' or f == 'Y':
                                                dfstock.sort_values(by = 'Unit_Price',axis = 0, ascending = True, inplace = True)
                                                dfstock.to_csv("Stock Details.csv")
                                                print('Saved Changes Exported Successfully!!!')
                                                print()
                                                input("Press Enter to continue...")
                                            elif f == 'n' or f == 'N':
                                                print('Saved Changes Not Exported!')
                                                print()
                                                input("Press Enter to continue...")
                                            else:
                                                print('Invalid Choice!')
                                                print()
                                                input('Press Enter to continue...')

                                        elif e == 2:    # SORTING THE TOTAL PRICE IN DESCENDING ORDER
                                            print(dfstock.sort_values(by = 'Unit_Price', axis = 0, ascending = False, inplace = False))
                                            f = input("DO YOU WANT TO EXPORT THE SAVE CHANGES? (y/n): ")
                                            if f == 'y' or f == 'Y':
                                                dfstock.sort_values(by = 'Unit_Price',axis = 0, ascending = False, inplace = True)
                                                dfstock.to_csv('Stock Details.csv')
                                                print('Saved Changes Exported Successfully!!!')
                                                print()
                                                input('Press Enter to Continue...')
                                            elif f == 'n' or f == 'N':
                                                print('Saved Changes Not Exported!')
                                                print()
                                                input('Press Enter to Continue...')
                                            else:
                                                print('Invalid Choice!')
                                                print()
                                                input('Press Enter to Continue...')
                                                print()
                                                  

                    elif b == 5:     #SEARCHING
                        print('''
                              
 ██████╗███████╗ █████╗ ██████╗  █████╗ ██╗  ██╗
██╔════╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██║  ██║
╚█████╗ █████╗  ███████║██████╔╝██║  ╚═╝███████║
 ╚═══██╗██╔══╝  ██╔══██║██╔══██╗██║  ██╗██╔══██║
██████╔╝███████╗██║  ██║██║  ██║╚█████╔╝██║  ██║
╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚════╝ ╚═╝  ╚═╝''')
                        print('''
                        *****𝙎𝙀𝘼𝙍𝘾𝙃 𝘽𝙔*********
                        * 1. CUSTOMER       *
                        * 2. STOCK          *
                        * 3. BILL           *
                        *********************''')
                        d = int(input("Enter ur Choice: "))
                        if d == 1:    #SEARCH BY CUSTOMER DETAILS
                            print('''
                            *****𝑺𝑬𝑨𝑹𝑪𝑯 𝑪𝑼𝑺𝑻𝑶𝑴𝑬𝑹 𝑩𝒀************
                            * 1. CUSTOMER NAME             *
                            * 2. PHONE NUMBER              *
                            ********************************''')
                            e = int(input("Enter ur Choice: "))
                            print()
                            if e == 1:   #SEARCHING CUSTOMER NAME
                                cname = input("Enter the Customer Name to search: ")
                                dfsearch = dfcustomer[dfcustomer['Cust_Name'] == cname] [['Phn_No','Email_Id','Address']]
                                if dfsearch.empty:
                                    print('Not Found!')
                                else:
                                    print(dfsearch)
                                input("Press Enter to Continue...")
                                
                            elif e == 2:      #SEARCHING PHONE NUMBER OF A CUSTOMER
                                pno = int(input("Enter the Phone Number to Search: "))
                                print()
                                dfsearch = dfcustomer[dfcustomer['Phn_No'] == pno][['Cust_Name','Email_Id']]
                                if dfsearch.empty:
                                    print()
                                    print('Record Not Found!')
                                else:
                                    print(dfsearch)
                                    print()
                                    input("Press Enter to Continue...")

                        elif d == 2:    #SEARCHING STOCK DETAILS
                            print('''
                            *****𝙎𝙀𝘼𝙍𝘾𝙃 𝙎𝙏𝙊𝘾𝙆 𝘽𝙔************
                            * 1. VENDOR NAME              *
                            * 2. STOCK ID                 *
                            * 3. GARMENT NAME             * 
                            *******************************''')
                            e = int(input("Enter ur Choice: "))
                            if e == 1:    #SEARCH BY VENDOR NAME
                                vname = input("Enter the Vendor Name: ")
                                dfsearch = dfstock[dfstock['Vendor_Name'] == vname][['Garment_Name','Qty_Purchased','Unit_Price','Total_Price']]
                                if dfsearch.empty:
                                    print('Record Not Found!')
                                else:
                                    print(dfsearch)
                                    input('Press Enter to Continue...')

                            elif e == 2:    #SEARCH BY STOCK ID
                                sid = input("Enter the Stock id: ")
                                if sid in dfstock.index:
                                    print(dfstock.loc[[sid]][['Garment_Name','Qty_Purchased','Unit_Price','Total_Price']])
                                else:
                                    print("Record Not Found!")
                                    print()
                                    input("Press Enter to Continue...")

                            elif e == 3:    #SEARCH BY Garment Name
                                gname = input("Enter the Garment Name: ")
                                dfsearch = dfstock[dfstock['Garment_Name'] == gname][['Qty_Purchased','Unit_Price','Vendor_Name']]
                                if dfsearch.empty:
                                    print("Record Not Found!")
                                    print()
                                    input("Press Enter to continue...")
                                else:
                                    print(dfsearch)
                                    print()
                                    input("Press Enter to Continue...")

                        elif d == 3:     #SEARCHING BILL DETAILS
                            print('''
                            *****𝙎𝙀𝘼𝙍𝘾𝙃 𝘽𝙄𝙇𝙇 𝘽𝙔*********
                            * 1. BILL ID           *
                            * 2. CUSTOMER ID       *
                            ************************''')
                            e = int(input("Enter ur Choice: "))
                            if e == 1:     #SEARCHING BILL ID
                                bid = input("Enter the Bill Id: ")
                                if bid in dfbilling.index:
                                    print(dfbilling.loc[bid][['Cust_ID','Bill_Date','Bill_Time','Garment_Name','Qty_Sold']])
                                else:
                                    print("Record Not Found!")
                                    print()
                                    input("Press Enter to Continue...")

                            elif e == 2:      #SEARCHING CUSTOMER ID
                                print(dfbilling[['Cust_ID']])
                                cid = input("Enter the customer id: ")
                                dfsearch = dfbilling[dfbilling['Cust_ID'] == cid][['Bill_Date','Bill_Time','Garment_Name','Qty_Sold']]
                                if dfsearch.empty:
                                    print("Record Not Found")
                                else:
                                    print(dfsearch)
                                    print()
                                    input("Press Enter to Continue...")

                                
                            
                    elif b == 6:                #GENERATING THE REPORTS
                        print('''
██████╗ ███████╗██████╗  █████╗ ██████╗ ████████╗ ██████╗
██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔══██╗╚══██╔══╝██╔════╝
██████╔╝█████╗  ██████╔╝██║  ██║██████╔╝   ██║   ╚█████╗ 
██╔══██╗██╔══╝  ██╔═══╝ ██║  ██║██╔══██╗   ██║    ╚═══██╗
██║  ██║███████╗██║     ╚█████╔╝██║  ██║   ██║   ██████╔╝
╚═╝  ╚═╝╚══════╝╚═╝      ╚════╝ ╚═╝  ╚═╝   ╚═╝   ╚═════╝ ''')
                        print('''
                        *****𝑹𝑬𝑷𝑶𝑹𝑻 𝑶𝑭***********
                        * 1. VENDOR            *
                        * 2. STOCK             *
                        * 3. PAYMENT           *
                        ************************''')
                        e = int(input("Enter your choice: "))
                        if e == 1:       #GENERATING THE VENDOR REPORT
                            vname = input("Enter the vendor name: ")
                            dfvname = dfstock[dfstock['Vendor_Name'] == vname]
                            if dfvname.empty:
                                print('No Such Vendor Found!')
                                print()
                                input("Press Enter to continue...")
                            else:
                                print(dfvname)
                                ans = input("DO YOU WANT TO EXPORT THE REPORT? (y/n): ")
                                print()
                                if ans == 'y' or ans  == 'Y':
                                    file = input("Enter the file name: ")
                                    print()
                                    dfvname.to_csv('Reports\\' + file + '.csv')
                                    print('Report Generated!!!')
                                    print()
                                    input("Press Enter to continue...")
                                elif ans == 'n' or ans == 'N':
                                    print()
                                    print("File not Exported!")
                                    print()
                                    input("Press Enter to continue...")
                                else:
                                    print("Invalid Choice!")
                                    print()
                                    input("Press Enter to continue...")
                        
                                    
                        elif e == 2:          #GENERATING THE STOCK REPORT  
                            gtype = input("Enter the garment type: ")
                            dfgtype = dfstock[dfstock['Garment_Type'] == gtype]
                            if dfgtype.empty:    
                                print("Record Not Found...")
                                input("Press Enter to continu...")
                            else:
                                print(dfgtype)    
                                k = input("Do you want to export this file? (y/n): ")
                                if k == 'y' or k == 'Y':    
                                    file = input("Enter the file name: ")
                                    dfgtype.to_csv("Reports\\" + file + '.csv')
                                    print("Report Genrated...")
                                    print()
                                    input("Press Enter to continue...")
                                elif k == 'n' or k == 'N':    
                                    print("File not Exported")
                                    print()
                                    print("Report Not Generated...")
                                    print()
                                    input("Press Enter to continue...")
                                else:     
                                    print('Invalid Choice...')
                                    print()
                                    input("Press Enter to continue...")

                        elif e == 3: #PAYMENT REPORT
                            print('\t\t\t\tGENERATING THE BILL REPORT THROUGH MODE OF TRANSACTION')
                            mot = input("Enter the mode of transaction: ")
                            dfmot = dfbilling[dfbilling['Mode_of_Trans'] == mot]
                            if dfmot.empty:   
                                print("Record Not Found")
                                print()
                                input("Press Enter to continue...")
                            else:     
                                print(dfmot)
                                k = input("Do you want to export this file? (y/n): ")
                                if k == 'y' or k == 'Y':      
                                    file = input("Ente the file name: ")
                                    print()
                                    dfmot.to_csv("Reports\\" + file + '.csv')
                                    print('Report Generated')
                                    print()
                                    input("Press Enter to continue...")
                                elif k == 'n' or k == 'N':    
                                    print()
                                    print("Report Not Generated...")
                                    print()
                                    input("Press Enter to continue...")
                                else:     
                                    print("Invalid Choice...")
                                    print()
                                    input("Press Enter to continue...")
                                

                    elif b == 7:              #ANALYSIS OF DATA THROUGH DATA VISUALIZATION
                       print('''
██████╗  █████╗ ████████╗ █████╗ 
██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗
██║  ██║███████║   ██║   ███████║
██║  ██║██╔══██║   ██║   ██╔══██║
██████╔╝██║  ██║   ██║   ██║  ██║
╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝

██╗   ██╗██╗ ██████╗██╗   ██╗ █████╗ ██╗     ██╗███████╗ █████╗ ████████╗██╗ █████╗ ███╗  ██╗
██║   ██║██║██╔════╝██║   ██║██╔══██╗██║     ██║╚════██║██╔══██╗╚══██╔══╝██║██╔══██╗████╗ ██║
╚██╗ ██╔╝██║╚█████╗ ██║   ██║███████║██║     ██║  ███╔═╝███████║   ██║   ██║██║  ██║██╔██╗██║
 ╚████╔╝ ██║ ╚═══██╗██║   ██║██╔══██║██║     ██║██╔══╝  ██╔══██║   ██║   ██║██║  ██║██║╚████║
  ╚██╔╝  ██║██████╔╝╚██████╔╝██║  ██║███████╗██║███████╗██║  ██║   ██║   ██║╚█████╔╝██║ ╚███║
   ╚═╝   ╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝ ╚════╝ ╚═╝  ╚══╝''')
                       print('''
                       *****𝘿𝘼𝙏𝘼 𝙑𝙄𝙎𝙐𝘼𝙇𝙄𝙕𝘼𝙏𝙄𝙊𝙉 𝘽𝙔************
                       * 1. BILL DETAILS               *
                       * 2. STOCK DETAILS              *
                       *********************************''')
                       e = int(input("Enter ur choice: "))
                       if e == 1:     # BILL DETAILS
                           print()
                           print('''What type of graph you want to make:
                                 1. BAR GRAPH
                                 2. LINE GRAPH
                                 3. PIE CHART''')
                           print()
                           f = int(input("Enter ur choice: "))
                           if f == 1:    #GENERATING THE BAR GRAPH
                               print('****GENERATING THE BAR GRAPH****')
                               print()
                               print('''Bar Graph on the basis of:
                                    1. Garment Type Wise Total Price
                                    2. Garment Name Wise Total Price
                                    3. Vendor Name Wise Total Price
                                    ''')
                               print()
                               w = int(input("Enter ur choice: "))
                               print()
                               if w == 1:      # BAR GRAPH GARMENT TYPE WISE
                                   gdf = dfstock.groupby('Garment_Type')
                                   graph_choice = input('1. All Records\n2. First 10\n3. Last 10')
                                   print()
                                   s = int(input("Enter ur choice: "))
                                   print()
                                   if s == 1:      # ALL RECORDS
                                       y = gdf.Total_Price.sum().sort_index()
                                       x = y.index
                                       plt.bar(x,y)
                                   elif s == 2:      # FIRST 10 RECORDS
                                       y = gdf.Total_Price.sum().sort_index().head(10)
                                       x = y.index
                                       plt.bar(x,y)
                                   elif s == 3:       # LAST 10 RECORDS
                                       y = gdf.Total_Price.sum().sort_index().tail(10)
                                       x = y.index
                                       plt.bar(x,y)
                                   plt.show()
                                   input("Press Enter to continue...")

                                   
                               elif w == 2:    #BAR GRAPH GARMENT NAME WISE
                                   gdf = dfstock.groupby('Garment_Name')
                                   graph_choice = input('1. All Records\n2. First 10\n3. Last 10')
                                   print()
                                   s = int(input("Enter ur choice: "))
                                   print()
                                   if s == 1:     #ALL RECORDS
                                       y = gdf.Total_Price.sum().sort_index()
                                       x = y.index
                                       plt.bar(x,y)
                                   elif s == 2:      # FIRST 10 RECORDS
                                       y = gdf.Total_Price.sum().sort_index().head(10)
                                       x = y.index
                                       plt.bar(x,y)
                                   elif s == 3:     #LAST 10 RECORDS
                                       y = gdf.Total_Price.sum().sort_index().tail(10)
                                       x = y.index
                                       plt.bar(x,y)
                                    
                                   plt.show()
                                   input("Press Enter to continue...")

                               elif w == 3:    #BAR GRAPH VENDOR TYPE WISE
                                   gdf = dfstock.groupby('Vendor_Name')
                                   graph_choice = input('1. All Records\n2. First 10\n3. Last 10')
                                   print()
                                   s = int(input("Enter ur choice: "))
                                   print()
                                   if s == 1:        # ALL RECORDS
                                       y = gdf.Total_Price.sum().sort_index()
                                       x = y.index
                                       plt.bar(x,y)
                                   elif s == 2:      # TOP 10 RECORDS
                                       y = gdf.Total_Price.sum().sort_index().head(10)
                                       x = y.index
                                       plt.bar(x,y)
                                   elif s == 3:          # LAST 10 RECORDS
                                       y = gdf.Total_Price.sum().sort_index().tail(10)
                                       x = y.index
                                       plt.bar(x,y)
                                    
                                   plt.show()
                                   input("Press Enter to continue...")

                           elif f == 2:         #GENERATING THE LINE GRAPH
                               print('****GENERATING THE LINE GRAPH****')
                               print()
                               print('''Line Graph on the basis of:
                                     1. Garment Type Wise Total Price
                                     2. Garment Name Wise Total Price
                                     3. Vendor Name Wise Total Price''')
                               print()
                               w = int(input("Enter ur choice: "))
                               print()
                               if w == 1:    # LINE GRAPH OF GARMENT TYPE WISE
                                   gdf = dfstock.groupby('Garment_Type')
                                   graph_choice = input('1. All Records\n2. First 10\n3. Last 10')
                                   print()
                                   s = int(input("Enter ur choice: "))
                                   if s == 1:     # ALL RECORDS
                                       y = gdf.Total_Price.sum().sort_index()
                                       x = y.index
                                       plt.plot(x,y)
                                   elif s == 2:      # FIRST 10 
                                       y = gdf.Total_Price.sum().head(10)
                                       x = y.index
                                       plt.plot(x,y)
                                   elif s == 3:    # LAST 10
                                       y = gdf.Total_Price.sum().tail(10)
                                       x = y.index
                                       plt.plot(x,y)
                                   plt.show()
                                   input("Press Enter to continue...")

                               elif w == 2:       # LINE GRAPH OF GARMENT NAMEWISE
                                   gdf = dfstock.groupby('Garment_Name')
                                   graph_choice = input('1. All Records\n2. First 10\n3. Last 10')
                                   print()
                                   s = int(input("Enter ur choice: "))
                                   if s == 1:     # ALL RECORDS
                                       y = gdf.Total_Price.sum().sort_index()
                                       x = y.index
                                       plt.plot(x,y)
                                   elif s == 2:      # FIRST 10 
                                       y = gdf.Total_Price.sum().head(10)
                                       x = y.index
                                       plt.plot(x,y)
                                   elif s == 3:    # LAST 10
                                       y = gdf.Total_Price.sum().tail(10)
                                       x = y.index
                                       plt.plot(x,y)
                                   plt.show()
                                   input("Press Enter to continue...")

                               elif w == 3:    # LINE GRAPH OF VENDOR NAME WISE
                                   gdf = dfstock.groupby('Vendor_Name')
                                   graph_choice = input('1. All Records\n2. First 10\n3. Last 10')
                                   print()
                                   s = int(input("Enter ur choice: "))
                                   if s == 1:     # ALL RECORDS
                                       y = gdf.Total_Price.sum().sort_index()
                                       x = y.index
                                       plt.plot(x,y)
                                   elif s == 2:      # FIRST 10 
                                       y = gdf.Total_Price.sum().head(10)
                                       x = y.index
                                       plt.plot(x,y)
                                   elif s == 3:    # LAST 10
                                       y = gdf.Total_Price.sum().tail(10)
                                       x = y.index
                                       plt.plot(x,y)
                                   plt.show()
                                   input("Press Enter to continue...")

                           elif f == 3:   #PIE CHART OF MODE OF TRANSACTION
                               print()
                               print('****GENERATING THE PIE CHART****')
                               data_pie = dfbilling['Mode_of_Trans'].value_counts().rename_axis('Mode_of_Trans').reset_index(name = 'Transaction_count')
                               plt.figure(figsize = (10,100))
                               plt.pie(data_pie.Transaction_count,labels = data_pie.Mode_of_Trans,startangle = 90,autopct = '%.1f%%')
                               plt.title('The Mode of Transaction')
                               plt.show()
                               print('Pie Chart Formed!!!')
                               print()
                               input("Press Enter to continue...")
                               
                           else:
                                print('Invalid Choice!')
                                print()
                                input("Press Enter to continue...")
                           

                       elif e == 2:     # STOCK DETAILS
                           print()
                           print('''What type of graph you want to make:
                                 1. BAR GRAPH
                                 2. LINE GRAPH
                                 3. PIE CHART''')
                           print()
                           f = int(input("Enter ur choice: "))
                           if f == 1:    #GENERATING THE BAR GRAPH
                               print('****GENERATING THE BAR GRAPH****')
                               print()
                               print('''Bar Graph on the basis of:
                                    1. Garment Type Wise Total Qty
                                    2. Garment Name Wise Total Qty
                                    3. Vendor Name Wise Total Qty
                                    ''')
                               print()
                               w = int(input("Enter ur choice: "))
                               print()
                               if w == 1:      # BAR GRAPH GARMENT TYPE WISE
                                   gdf = dfstock.groupby('Garment_Type')
                                   graph_choice = input('1. All Records\n2. First 10\n3. Last 10')
                                   print()
                                   s = int(input("Enter ur choice: "))
                                   print()
                                   if s == 1:      # ALL RECORDS
                                       y = gdf.Qty_Purchased.sum().sort_index()
                                       x = y.index
                                       plt.bar(x,y)
                                   elif s == 2:      # FIRST 10 RECORDS
                                       y = gdf.Qty_Purchased.sum().sort_index().head(10)
                                       x = y.index
                                       plt.bar(x,y)
                                   elif s == 3:       # LAST 10 RECORDS
                                       y = gdf.Qty_Purchased.sum().sort_index().tail(10)
                                       x = y.index
                                       plt.bar(x,y)
                                   plt.show()
                                   input("Press Enter to continue...")

                                   
                               elif w == 2:    #BAR GRAPH GARMENT NAME WISE
                                   gdf = dfstock.groupby('Garment_Name')
                                   graph_choice = input('1. All Records\n2. First 10\n3. Last 10')
                                   print()
                                   s = int(input("Enter ur choice: "))
                                   print()
                                   if s == 1:     #ALL RECORDS
                                       y = gdf.Qty_Purchased.sum().sort_index()
                                       x = y.index
                                       plt.bar(x,y)
                                   elif s == 2:      # FIRST 10 RECORDS
                                       y = gdf.Qty_Purchased.sum().sort_index().head(10)
                                       x = y.index
                                       plt.bar(x,y)
                                   elif s == 3:     #LAST 10 RECORDS
                                       y = gdf.Qty_Purchased.sum().sort_index().tail(10)
                                       x = y.index
                                       plt.bar(x,y)
                                    
                                   plt.show()
                                   input("Press Enter to continue...")

                               elif w == 3:    #BAR GRAPH VENDOR TYPE WISE
                                   gdf = dfstock.groupby('Vendor_Name')
                                   graph_choice = input('1. All Records\n2. First 10\n3. Last 10')
                                   print()
                                   s = int(input("Enter ur choice: "))
                                   print()
                                   if s == 1:        # ALL RECORDS
                                       y = gdf.Qty_Purchased.sum().sort_index()
                                       x = y.index
                                       plt.bar(x,y)
                                   elif s == 2:      # TOP 10 RECORDS
                                       y = gdf.Qty_Purchased.sum().sort_index().head(10)
                                       x = y.index
                                       plt.bar(x,y)
                                   elif s == 3:          # LAST 10 RECORDS
                                       y = gdf.Qty_Purchased.sum().sort_index().tail(10)
                                       x = y.index
                                       plt.bar(x,y)
                                    
                                   plt.show()
                                   input("Press Enter to continue...")

                           elif f == 2:         #GENERATING THE LINE GRAPH
                               print('****GENERATING THE LINE GRAPH****')
                               print()
                               print('''Line Graph on the basis of:
                                     1. Garment Type Wise Total Price
                                     2. Garment Name Wise Total Price
                                     3. Vendor Name Wise Total Price''')
                               print()
                               w = int(input("Enter ur choice: "))
                               print()
                               if w == 1:    # LINE GRAPH OF GARMENT TYPE WISE
                                   gdf = dfstock.groupby('Garment_Type')
                                   graph_choice = input('1. All Records\n2. First 10\n3. Last 10')
                                   print()
                                   s = int(input("Enter ur choice: "))
                                   if s == 1:     # ALL RECORDS
                                       y = gdf.Qty_Purchased.sum().sort_index()
                                       x = y.index
                                       plt.plot(x,y)
                                   elif s == 2:      # FIRST 10 
                                       y = gdf.Qty_Purchased.sum().head(10)
                                       x = y.index
                                       plt.plot(x,y)
                                   elif s == 3:    # LAST 10
                                       y = gdf.Qty_Purchased.sum().tail(10)
                                       x = y.index
                                       plt.plot(x,y)
                                   plt.show()
                                   input("Press Enter to continue...")

                               elif w == 2:       # LINE GRAPH OF GARMENT NAMEWISE
                                   gdf = dfstock.groupby('Garment_Name')
                                   graph_choice = input('1. All Records\n2. First 10\n3. Last 10')
                                   print()
                                   s = int(input("Enter ur choice: "))
                                   if s == 1:     # ALL RECORDS
                                       y = gdf.Qty_Purchased.sum().sort_index()
                                       x = y.index
                                       plt.plot(x,y)
                                   elif s == 2:      # FIRST 10 
                                       y = gdf.Qty_Purchased.sum().head(10)
                                       x = y.index
                                       plt.plot(x,y)
                                   elif s == 3:    # LAST 10
                                       y = gdf.Qty_Purchased.sum().tail(10)
                                       x = y.index
                                       plt.plot(x,y)
                                   plt.show()
                                   input("Press Enter to continue...")

                               elif w == 3:    # LINE GRAPH OF VENDOR NAME WISE
                                   gdf = dfstock.groupby('Vendor_Name')
                                   print('1. All Records\n2. First 10\n3. Last 10')
                                   print()
                                   s = int(input("Enter ur choice: "))
                                   if s == 1:     # ALL RECORDS
                                       y = gdf.Qty_Purchased.sum().sort_index()
                                       x = y.index
                                       plt.plot(x,y)
                                   elif s == 2:      # FIRST 10 
                                       y = gdf.Qty_Purchased.sum().head(10)
                                       x = y.index
                                       plt.plot(x,y)
                                   elif s == 3:    # LAST 10
                                       y = gdf.Qty_Purchased.sum().tail(10)
                                       x = y.index
                                       plt.plot(x,y)
                                   plt.show()
                                   input("Press Enter to continue...")

                           elif f == 3:         # PIE CHART
                                print('****GENERATIN THE PIE CHART****')
                                print()
                                data_pie = dfstock['Garment_Type'].value_counts().rename_axis('Garment_Type').reset_index(name = 'Garment_count')
                                plt.figure(figsize = (10,100))
                                plt.pie(data_pie.Garment_count,labels = data_pie.Garment_Type,startangle = 90,autopct = '%.1f%%')
                                plt.title('Garment Type')
                                plt.show()
                                print('Pie Chart Formed!!!')
                                print()
                                input("Press Enter to continue...")
                           
                               

                    elif b == 8:                 #LOGOUT FROM THE MENU
                        print('''

▀█▀ █ █ ▄▀█ █▄ █ █▄▀ █▀       
 █  █▀█ █▀█ █ ▀█ █ █ ▄█ ▄ ▄ ▄''')
                        break
                         
            
    elif a == 2:       #EXIT FROM THE PROGRAM
        print('THANKS FOR USING OUR PROGRAM....HAVE A GREAT DAY AHEAD!!!!!')
        break
    else:
        print("Inavlid Choice!!!")
        print()
        input("Press enter to continue...")
