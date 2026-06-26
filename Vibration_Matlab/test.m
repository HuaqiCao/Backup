a=0;
d=20;
l=30;
k1=1;
k2=4*k1*(l*d^2-(sqrt(a^2+d^2))^3)/(sqrt(a^2+d^2))^3;
fprintf('k2=%0.5f\n',k2);
%f=2*k1*(l-sqrt((a-x)^2+d^2))/sqrt((a-x)^2+d^2)*(a-x)-2*k1*(l-sqrt((a+x)^2+d^2))/sqrt((a+x)^2+d^2)*(a+x)+k2*x;

x = linspace(-8, 8, 1000); 
f = 2*k1.*(l - sqrt((a-x).^2 + d.^2)) ./ sqrt((a-x).^2 + d.^2) .* (a-x) ...
    - 2*k1.*(l - sqrt((a+x).^2 + d.^2)) ./ sqrt((a+x).^2 + d.^2) .* (a+x) ...
    + k2.*x;

figure;
plot(x, f, 'b-', 'LineWidth', 2);
grid on;
xlabel('位移 x');
ylabel('恢复力 f');
ylim([-4 4]);
title('非线性弹簧力-位移曲线');