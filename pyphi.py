import numpy as np
from scipy.special import factorial

def z2n(X,X_nan_map):
    X[X_nan_map==1] = np.nan
    return X

def n2z(X):
    X_nan_map = np.isnan(X)            
    if X_nan_map.any():
        X_nan_map       = X_nan_map*1
        X[X_nan_map==1] = 0
    else:
        X_nan_map       = X_nan_map*1
    return X,X_nan_map

def mean(X):
    X_nan_map = np.isnan(X)
    X_ = X.copy()
    if X_nan_map.any():
        X_nan_map       = X_nan_map*1
        X_[X_nan_map==1] = 0
        aux             = np.sum(X_nan_map,axis=0)
        #Calculate mean without accounting for NaN's
        x_mean = np.sum(X_,axis=0,keepdims=1)/(np.ones((1,X_.shape[1]))*X_.shape[0]-aux)
    else:
        x_mean = np.mean(X_,axis=0,keepdims=1)
    return x_mean

def std(X):
    x_mean=mean(X)
    x_mean=np.tile(x_mean,(X.shape[0],1))
    X_nan_map = np.isnan(X)
    if X_nan_map.any():
        X_nan_map             = X_nan_map*1
        X_                    = X.copy()
        X_[X_nan_map==1]      = 0
        aux_mat               = (X_-x_mean)**2
        aux_mat[X_nan_map==1] = 0
        aux                   = np.sum(X_nan_map,axis=0)
        #Calculate mean without accounting for NaN's
        x_std = np.sqrt((np.sum(aux_mat,axis=0,keepdims=1))/(np.ones((1,X_.shape[1]))*(X_.shape[0]-1-aux)))
    else:
        x_std = np.sqrt(np.sum((X-x_mean)**2,axis=0,keepdims=1)/(np.ones((1,X.shape[1]))*(X.shape[0]-1)))
    return x_std
   
def meancenterscale(X,*,mcs=True):
    if isinstance(mcs,bool):
        if mcs:
            x_mean = mean(X)
            x_std  = std(X)
            X      = X-np.tile(x_mean,(X.shape[0],1))
            X      = X/np.tile(x_std,(X.shape[0],1))
    elif mcs=='center':
         x_mean = mean(X)
         X      = X-np.tile(x_mean,(X.shape[0],1))
         x_std  = np.ones((1,X.shape[1]))
    elif mcs=='autoscale':
         x_std  = std(X) 
         X      = X/np.tile(x_std,(X.shape[0],1))
         x_mean = np.zeros((1,X.shape[1]))
    return X,x_mean,x_std
 
    
def pca(X,A,*,mcs=True,md_algorithm='nipals',force_nipals=False):
    X_=X.copy()
    if isinstance(mcs,bool):
        if mcs:
            #Mean center and autoscale  
            X_,x_mean,x_std = meancenterscale(X_)          
    elif mcs=='center':
        X_,x_mean,x_std = meancenterscale(X_,mcs='center')
        #only center
    elif mcs=='autoscale':
        #only autoscale
        X_,x_mean,x_std = meancenterscale(X_,mcs='autoscale')
        
    #Generate Missing Data Map    
    X_nan_map = np.isnan(X_)
    not_Xmiss = (np.logical_not(X_nan_map))*1
    
    if not(X_nan_map.any()) and not(force_nipals):
        #no missing elements
        print('phi.pca is using SVD')
        TSS   = np.sum(X_**2)
        TSSpv = np.sum(X_**2,axis=0)
        if X_.shape[1]>X_.shape[0]:
             [U,S,Th]   = np.linalg.svd(X_ @ X_.T)
             T          = Th.T 
             T          = T[:,0:A]
             P          = T.T @ X
             for a in list(range(A)):
                 P[:,a] = P[:,a]/np.linalg.norm(P[:,a])
        elif X_.shape[0]>=X_.shape[1]:
             [U,S,Ph]   = np.linalg.svd(X_.T @ X_)
             P          = Ph.T
             P          = P[:,0:A]
             T          = X_ @ P
        for a in list(range(A)):
            X_ = X_-T[:,[a]]@P[:,[a]].T
            if a==0:
                r2   = 1-np.sum(X_**2)/TSS
                r2pv = 1-np.sum(X_**2,axis=0)/TSSpv
                r2pv = r2pv.reshape(-1,1)
            else:
                r2   = np.hstack((r2,  1-np.sum(X_**2)/TSS))
                aux_ = 1-(np.sum(X_**2,axis=0)/TSSpv)
                r2pv = np.hstack((r2pv,aux_.reshape(-1,1)))
        for a in list(range(A-1,0,-1)):
             r2[a]     = r2[a]-r2[a-1]
             r2pv[:,a] = r2pv[:,a]-r2pv[:,a-1]
        pca_obj={'T':T,'P':P,'r2x':r2,'r2xpv':r2pv,'mx':x_mean,'sx':x_std}
        return pca_obj
    else:
        if md_algorithm=='nipals':
             #use nipals
             print('phi.pca is using NIPALS')
             X_,dummy=n2z(X_)
             epsilon=1E-10
             maxit=10000
             TSS   = np.sum(X_**2)
             TSSpv = np.sum(X_**2,axis=0)
             #T=[];
             #P=[];
             #r2=[];
             #r2pv=[];
             #numIT=[];
             for a in list(range(A)):
                 # Select column with largest variance as initial guess
                 ti = X_[:,[np.argmax(std(X_))]]
                 Converged=False
                 num_it=0
                 while Converged==False:
                      #Step 1. p(i)=t' x(i)/t't
                      timat=np.tile(ti,(1,X_.shape[1]))
                      pi=(np.sum(X_*timat,axis=0))/(np.sum((timat*not_Xmiss)**2,axis=0))
                      #Step 2. Normalize p to unit length.
                      pi=pi/np.linalg.norm(pi)
                      #Step 3. tnew= (x*p) / (p'p);
                      pimat=np.tile(pi,(X_.shape[0],1))
                      tn= X_ @ pi.T
                      ptp=np.sum((pimat*not_Xmiss)**2,axis=1)
                      tn=tn/ptp
                      pi=pi.reshape(-1,1)
                      if abs((np.linalg.norm(ti)-np.linalg.norm(tn)))/(np.linalg.norm(ti)) < epsilon:
                          Converged=True
                      if num_it > maxit:
                          Converged=True
                      if Converged:
                          print('# Iterations for PC #'+str(a+1)+': ',str(num_it))
                          if a==0:
                              T=ti
                              P=pi
                          else:
                              T=np.hstack((T,tn.reshape(-1,1)))
                              P=np.hstack((P,pi))                           
                          # Deflate X leaving missing as zeros (important!)
                          X_=(X_- ti @ pi.T)*not_Xmiss
                          if a==0:
                              r2   = 1-np.sum(X_**2)/TSS
                              r2pv = 1-np.sum(X_**2,axis=0)/TSSpv
                              r2pv = r2pv.reshape(-1,1)
                          else:
                              r2   = np.hstack((r2,1-np.sum(X_**2)/TSS))
                              aux_ = 1-np.sum(X_**2,axis=0)/TSSpv
                              aux_ = aux_.reshape(-1,1)
                              r2pv = np.hstack((r2pv,aux_))
                      else:
                          num_it = num_it + 1
                          ti = tn.reshape(-1,1)
                 if a==0:
                     numIT=num_it
                 else:
                     numIT=np.hstack((numIT,num_it))
                     
             for a in list(range(A-1,0,-1)):
                 r2[a]     = r2[a]-r2[a-1]
                 r2pv[:,a] = r2pv[:,a]-r2pv[:,a-1]
             pca_obj={'T':T,'P':P,'r2x':r2,'r2xpv':r2pv,'mx':x_mean,'sx':x_std}    
             return pca_obj                            
        elif md_algorithm=='nlp':
            #use NLP per Lopez-Negrete et al. J. Chemometrics 2010; 24: 301–311
            pca_obj=1
            return pca_obj
           
    
  
def pls(X,Y,A,*,mcsX=True,mcsY=True,md_algorithm='nipals',force_nipals=False):
    X_=X.copy()
    Y_=Y.copy()
    if isinstance(mcsX,bool):
        if mcsX:
            #Mean center and autoscale  
            X_,x_mean,x_std = meancenterscale(X_)
    elif mcsX=='center':
        X_,x_mean,x_std = meancenterscale(X_,mcs='center')
        #only center      
    elif mcsX=='autoscale':
        #only autoscale
        X_,x_mean,x_std = meancenterscale(X_,mcs='autoscale')
        
    if isinstance(mcsY,bool):
        if mcsY:
            #Mean center and autoscale  
            Y_,y_mean,y_std = meancenterscale(Y_)
    elif mcsY=='center':
        Y_,y_mean,y_std = meancenterscale(Y_,mcs='center')
        #only center      
    elif mcsY=='autoscale':
        #only autoscale
        Y_,y_mean,y_std = meancenterscale(Y_,mcs='autoscale')    
        
    #Generate Missing Data Map    
    X_nan_map = np.isnan(X_)
    not_Xmiss = (np.logical_not(X_nan_map))*1
    Y_nan_map = np.isnan(Y_)
    not_Ymiss = (np.logical_not(Y_nan_map))*1
    
    if (not(X_nan_map.any()) and not(Y_nan_map.any())) and not(force_nipals):
        #no missing elements
        print('phi.pls is using SVD')
        TSSX   = np.sum(X_**2)
        TSSXpv = np.sum(X_**2,axis=0)
        TSSY   = np.sum(Y_**2)
        TSSYpv = np.sum(Y_**2,axis=0)
        
        for a in list(range(A)):
            [U_,S,Wh]   = np.linalg.svd((X_.T @ Y_) @ (Y_.T @ X_))
            w          = Wh.T
            w          = w[:,[0]]
            t          = X_ @ w
            q          = Y_.T @ t / (t.T @ t)
            u          = Y_ @ q /(q.T @ q)
            p          = X_.T  @ t / (t.T @ t)
            
            X_ = X_- t @ p.T
            Y_ = Y_- t @ q.T
            
            if a==0:
                W     = w.reshape(-1,1)
                T     = t.reshape(-1,1)
                Q     = q.reshape(-1,1)
                U     = u.reshape(-1,1)
                P     = p.reshape(-1,1)
                
                r2X   = 1-np.sum(X_**2)/TSSX
                r2Xpv = 1-np.sum(X_**2,axis=0)/TSSXpv
                r2Xpv = r2Xpv.reshape(-1,1)
                
                r2Y   = 1-np.sum(Y_**2)/TSSY
                r2Ypv = 1-np.sum(Y_**2,axis=0)/TSSYpv
                r2Ypv = r2Ypv.reshape(-1,1)
            else:
                W     = np.hstack((W,w.reshape(-1,1)))
                T     = np.hstack((T,t.reshape(-1,1)))
                Q     = np.hstack((Q,q.reshape(-1,1)))
                U     = np.hstack((U,u.reshape(-1,1)))
                P     = np.hstack((P,p.reshape(-1,1)))
                
                r2X_   = 1-np.sum(X_**2)/TSSX
                r2Xpv_ = 1-np.sum(X_**2,axis=0)/TSSXpv
                r2Xpv_ = r2Xpv_.reshape(-1,1)
                r2X    = np.hstack((r2X,r2X_))
                r2Xpv  = np.hstack((r2Xpv,r2Xpv_))
                
                r2Y_   = 1-np.sum(Y_**2)/TSSY
                r2Ypv_ = 1-np.sum(Y_**2,axis=0)/TSSYpv
                r2Ypv_ = r2Ypv_.reshape(-1,1)
                r2Y    = np.hstack((r2Y,r2Y_))
                r2Ypv  = np.hstack((r2Ypv,r2Ypv_))
        for a in list(range(A-1,0,-1)):
            r2X[a]     = r2X[a]-r2X[a-1]
            r2Xpv[:,a] = r2Xpv[:,a]-r2Xpv[:,a-1]
            r2Y[a]     = r2Y[a]-r2Y[a-1]
            r2Ypv[:,a] = r2Ypv[:,a]-r2Ypv[:,a-1]
        
        pls_obj={'T':T,'P':P,'Q':Q,'W':W,'U':U,'r2x':r2X,'r2xpv':r2Xpv,'mx':x_mean,'sx':x_std,'r2y':r2Y,'r2ypv':r2Ypv,'my':y_mean,'sy':y_std}  
        return pls_obj
    else:
        if md_algorithm=='nipals':
             #use nipals
             print('phi.pls is using NIPALS')
             X_,dummy=n2z(X_)
             Y_,dummy=n2z(Y_)
             epsilon=1E-10
             maxit=10000

             TSSX   = np.sum(X_**2)
             TSSXpv = np.sum(X_**2,axis=0)
             TSSY   = np.sum(Y_**2)
             TSSYpv = np.sum(Y_**2,axis=0)
             
             #T=[];
             #P=[];
             #r2=[];
             #r2pv=[];
             #numIT=[];
             for a in list(range(A)):
                 # Select column with largest variance in Y as initial guess
                 ui = Y_[:,[np.argmax(std(Y_))]]
                 Converged=False
                 num_it=0
                 while Converged==False:
                      # %Step 1. w=X'u/u'u
                      uimat=np.tile(ui,(1,X_.shape[1]))
                      wi=(np.sum(X_*uimat,axis=0))/(np.sum((uimat*not_Xmiss)**2,axis=0))
                      #Step 2. Normalize w to unit length.
                      wi=wi/np.linalg.norm(wi)
                      #Step 3. ti= (Xw)/(w'w);
                      wimat=np.tile(wi,(X_.shape[0],1))
                      ti= X_ @ wi.T
                      wtw=np.sum((wimat*not_Xmiss)**2,axis=1)
                      ti=ti/wtw
                      ti=ti.reshape(-1,1)
                      wi=wi.reshape(-1,1)
                      #Step 4 q=Y't/t't
                      timat=np.tile(ti,(1,Y_.shape[1]))
                      qi=(np.sum(Y_*timat,axis=0))/(np.sum((timat*not_Ymiss)**2,axis=0))
                      #Step 5 un=(Yq)/(q'q)
                      qimat=np.tile(qi,(Y_.shape[0],1))
                      qi=qi.reshape(-1,1)
                      un= Y_ @ qi
                      qtq=np.sum((qimat*not_Ymiss)**2,axis=1)
                      qtq=qtq.reshape(-1,1)
                      un=un/qtq
                      un=un.reshape(-1,1)
                      
                      if abs((np.linalg.norm(ui)-np.linalg.norm(un)))/(np.linalg.norm(ui)) < epsilon:
                          Converged=True
                      if num_it > maxit:
                          Converged=True
                      if Converged:
                          print('# Iterations for LV #'+str(a+1)+': ',str(num_it))
                          # Calculate P's for deflation p=Xt/(t't)      
                          timat=np.tile(ti,(1,X_.shape[1]))
                          pi=(np.sum(X_*timat,axis=0))/(np.sum((timat*not_Xmiss)**2,axis=0))
                          pi=pi.reshape(-1,1)
                          # Deflate X leaving missing as zeros (important!)
                          X_=(X_- ti @ pi.T)*not_Xmiss
                          Y_=(Y_- ti @ qi.T)*not_Ymiss
                          
                          if a==0:
                              T=ti
                              P=pi
                              W=wi
                              U=un
                              Q=qi
                              r2X   = 1-np.sum(X_**2)/TSSX
                              r2Xpv = 1-np.sum(X_**2,axis=0)/TSSXpv
                              r2Xpv = r2Xpv.reshape(-1,1)
                              r2Y   = 1-np.sum(Y_**2)/TSSY
                              r2Ypv = 1-np.sum(Y_**2,axis=0)/TSSYpv
                              r2Ypv = r2Ypv.reshape(-1,1)
                          else:
                              T=np.hstack((T,ti.reshape(-1,1)))
                              U=np.hstack((U,un.reshape(-1,1)))
                              P=np.hstack((P,pi))   
                              W=np.hstack((W,wi))
                              Q=np.hstack((Q,qi))
                                             
                              r2X_   = 1-np.sum(X_**2)/TSSX
                              r2Xpv_ = 1-np.sum(X_**2,axis=0)/TSSXpv
                              r2Xpv_ = r2Xpv_.reshape(-1,1)
                              r2X    = np.hstack((r2X,r2X_))
                              r2Xpv  = np.hstack((r2Xpv,r2Xpv_))
                
                              r2Y_   = 1-np.sum(Y_**2)/TSSY
                              r2Ypv_ = 1-np.sum(Y_**2,axis=0)/TSSYpv
                              r2Ypv_ = r2Ypv_.reshape(-1,1)
                              r2Y    = np.hstack((r2Y,r2Y_))
                              r2Ypv  = np.hstack((r2Ypv,r2Ypv_))
                      else:
                          num_it = num_it + 1
                          ui = un
                 if a==0:
                     numIT=num_it
                 else:
                     numIT=np.hstack((numIT,num_it))
                     
             for a in list(range(A-1,0,-1)):
                 r2X[a]     = r2X[a]-r2X[a-1]
                 r2Xpv[:,a] = r2Xpv[:,a]-r2Xpv[:,a-1]
                 r2Y[a]     = r2Y[a]-r2Y[a-1]
                 r2Ypv[:,a] = r2Ypv[:,a]-r2Ypv[:,a-1]
        
             pls_obj={'T':T,'P':P,'Q':Q,'W':W,'U':U,'r2x':r2X,'r2xpv':r2Xpv,'mx':x_mean,'sx':x_std,'r2y':r2Y,'r2ypv':r2Ypv,'my':y_mean,'sy':y_std}  
             return pls_obj   
                         
        elif md_algorithm=='nlp':
            #use NLP per Lopez-Negrete et al. J. Chemometrics 2010; 24: 301–311
            pca_obj=1
            return pca_obj

def snv (x):
    if x.ndim ==2:
        mean_x = np.mean(x,axis=1,keepdims=1)     
        mean_x = np.tile(mean_x,(1,x.shape[1]))
        x      = x - mean_x
        std_x  = np.sum(x**2,axis=1)/(x.shape[1]-1)
        std_x  = np.sqrt(std_x)
        std_x  = np.reshape(std_x,(len(std_x),1))
        std_x =  np.tile(std_x,(1,x.shape[1]))
        x      = x/std_x
        return x
    else:
        x = x - np.mean(x)
        stdx = np.sqrt(np.sum(x**2)/(len(x)-1))
        x = x/stdx
        return x
    
def savgol(ws,od,op,Dm):
    if Dm.ndim==1: 
        l = Dm.shape[0]
    else:
        l = Dm.shape[1]
        
    x_vec=np.arange(-ws,ws+1)
    x_vec=np.reshape(x_vec,(len(x_vec),1))
    X = np.ones((2*ws+1,1))
    for oo in np.arange(1,op+1):
        X=np.hstack((X,x_vec**oo))
    XtXiXt=np.linalg.inv(X.T @ X) @ X.T
    coeffs=XtXiXt[od,:] * factorial(od)
    coeffs=np.reshape(coeffs,(1,len(coeffs)))
    for i in np.arange(1,l-2*ws+1):
        if i==1:
            M=np.hstack((coeffs,np.zeros((1,l-2*ws-1))))
        elif i < l-2*ws:
            m_= np.hstack((np.zeros((1,i-1)), coeffs))
            m_= np.hstack((m_,np.zeros((1,l-2*ws-1-i+1))))
            M = np.vstack((M,m_))
        else:
            m_=np.hstack((np.zeros((1,l-2*ws-1)),coeffs))
            M = np.vstack((M,m_))
    if Dm.ndim==1: 
        Dm_sg= M @ Dm
    else:
        for i in np.arange(1,Dm.shape[0]+1):
            dm_ = M @ Dm[i-1,:]
            if i==1:
                Dm_sg=dm_
            else:
                Dm_sg=np.vstack((Dm_sg,dm_))
    return Dm_sg,M
       