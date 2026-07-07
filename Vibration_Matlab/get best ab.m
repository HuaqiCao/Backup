clear; clc;

% 1. 定义已知参数（根据你的实际问题修改）
k1=0.3785;
k2=0.2013;
k3=0.6026;
l1=39.7;
l2=39.7;

% 2. 定义方程组函数句柄
% x(1) 和 x(2) 是两个未知数
fun = @(x) my_equations(x, k1,k2,k3,l1,l2);

% 3. 设置初始猜测值（非常重要！）
x0 = [15.2, 20];

% 4. 设置求解选项
options = optimoptions('fsolve', ...
    'Display', 'iter', ...          % 显示迭代过程
    'MaxIterations', 1000, ...      % 最大迭代次数
    'FunctionTolerance', 1e-10);    % 精度

% 5. 调用 fsolve 求解
[x, fval, exitflag] = fsolve(fun, x0, options);

% 6. 输出结果
fprintf('========== 求解结果 ==========\n');
fprintf('x1 = %.6f\n', x(1));
fprintf('x2 = %.6f\n', x(2));
%fprintf('方程残差 = %e\n', norm(fval));
%fprintf('退出标志 = %d (1表示收敛)\n', exitflag);
%end
%end
%end
%end
%end

function F=my_equations(x,k1,k2,k3,l1,l2)
x1=x(1);
x2=x(2);
F(1)=-2*3*k1*l1*x2^2/(x1^2+x2^2)^(3/2)-3*k2*l2/x2+6*k1+3*k2+k3;
F(2)=(k2*l1*(x1^2+x2^2)^(7/2))/(k1*l2*(8*x1^2-2*x2^2)*x2^5)-1;
end