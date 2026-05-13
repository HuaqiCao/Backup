%%已知弹簧的d&D_out&L,求K
d_range = 0.2:0.1:3;
D_out_range = 5:1:30;
for d=d_range
    for D_out=D_out_range
        % d = 0.8; %mm
        %D_out = 10;
        L = 90;
        G = 77000;

        D = D_out - d;
        C = D/d;
        p = 0.5*D;
        n = (L-2*d)/p;
        k = (G*D)/(8*(C^4)*n); %N/mm
        k1 = (G*d^4)/(8*D^3*n); %N/mm
        if k >0.244 && k <0.26
            fprintf('D=%.1fmm, C=%.1f, p=%.1fmm, n=%.1f, k=%.3fN/mm, k1=%.3fN/mm\n\n', D, C, p, n, k, k1);
            fprintf('d=%.1fmm, D_out=%.1f, k=%.5fN/mm, k1=%.4fN/mm\n\n', d, D_out, k, k1);
        end
    end
end