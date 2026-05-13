%%已知弹簧的d&D_out&L,求K
d = 0.5; %mm
D_out = 7; 
L = 40;
G = 77000;

D = D_out - d; 
C = D/d;
p = 0.5*D;
n = (L-2*d)/p;
k = (G*D)/(8*(C^4)*n); %N/mm
k1 = (G*d^4)/(8*D^3*n); %N/mm
fprintf('D=%.1fmm, C=%.1f, p=%.1fmm, n=%.1f, k=%.3fN/mm, k1=%.3fN/mm\n\n', D, C, p, n, k, k1);