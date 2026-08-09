d=27.96;
a=21.26;
l1=49.8;
l2=49.8;
k1=0.3785;
k2=0.2406;
k3=0.2013;
x = linspace(-20, 20, 1000); 
f = 3.*k1.*(l1 - sqrt((a-x).^2 + d.^2)) ./ sqrt((a-x).^2 + d.^2) .* (a-x) ...
    - 3.*k1.*(l1 - sqrt((a+x).^2 + d.^2)) ./ sqrt((a+x).^2 + d.^2) .* (a+x) ...
    - 3 .* k3 .* (l2 - sqrt(x.^2 + d.^2)) .* x ./ sqrt(x.^2 + d.^2)+ k2.*x;

figure;
plot(x, f, 'b-', 'LineWidth', 2);
grid on;
xlabel('位移 x');
ylabel('恢复力 f');
title('非线性弹簧力-位移曲线');