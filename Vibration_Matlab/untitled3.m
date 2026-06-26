d=20;
a=15.2;
l=39.7;
k1=0.1419;
k2=0.6026;
k3=0.0757;
x = linspace(-15, 15, 1000); 
f = 8.*k1.*(l - sqrt((a-x).^2 + d.^2)) ./ sqrt((a-x).^2 + d.^2) .* (a-x) ...
    - 8.*k1.*(l - sqrt((a+x).^2 + d.^2)) ./ sqrt((a+x).^2 + d.^2) .* (a+x) ...
    - 8 .* k3 .* (l - sqrt(x.^2 + d.^2)) .* x ./ sqrt(x.^2 + d.^2)+ k2.*x;

figure;
plot(x, f, 'b-', 'LineWidth', 2);
grid on;
xlabel('位移 x');
ylabel('恢复力 f');
title('非线性弹簧力-位移曲线');