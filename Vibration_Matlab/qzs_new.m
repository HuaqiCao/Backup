clear; clc;

%% 目标无量纲参数
delta_hat_target = 0.5;      % δ̂ = δ / sqrt(a^2 + h1^2) -> (δ_target)
a_hat_target     = 0.755;    % â = a / sqrt(a^2 + h1^2) ->（h1_target）
alpha_target     = 0.942;    % α = k1/k2 (遍历k1->K2)
alpha1_target    = 0.501;    % α₁ = k3/k2 (K2->K3)
gamma_target     = 2.143;    % γ = h/d

fprintf('目标无量纲参数:\n');
fprintf('  δ̂_target = %.3f, â_target = %.3f, α_target = %.3f, α₁_target = %.3f, γ_target = %.3f\n\n', ...
    delta_hat_target, a_hat_target, alpha_target, alpha1_target, gamma_target);

%% 侧边弹簧的水平投影距离（可调）
a_target = 20;     %mm

%% 弹簧材料参数（可调）
tau_p =70; %平均许用切应力Mpa
G=77000; %Mpa

C_range = 5:0.1:12; %旋绕比 K2
C1_range = 5:0.1:12; %旋绕比 上&下
C2_range = 5:0.1:12; %旋绕比 中

ratio = 0.5; %K2
ratio1 = 0.5; %上&下
ratio2= 0.5; %中

%% load mass
M = 2;              % K2&kg
M1 = 0.7;             % 上&下
M2 = 0.5;             % 中
g = 9.81;

%% 由 â = a / sqrt(a^2 + h1^2) 反求 h1
h1_target = sqrt(a_target^2 * (1/a_hat_target^2 - 1));
fprintf('由 â_target & a_target=%0.1fmm 计算得到: h₁_target = %.1f mm\n\n',a_target,h1_target);

%% 由 δ̂ = δ / sqrt(a^2 + h1^2) 求 δ
% δ = δ̂ * sqrt(a^2 + h1_target^2)
delta_target = delta_hat_target * sqrt(a_target^2 + h1_target^2);

%% 斜弹簧原始长度（三根弹簧原长相同）
L1 = sqrt(a_target^2 + h1_target^2) + delta_target; %上
fprintf('由 δ̂_target & a_target & h1_target 计算得到: δ_target = %.1f mm, L1(上) = %.1f mm\n\n',delta_target, L1);

%% 由 γ 计算 d，进而计算h和h2
% d = h / γ_target
d_target = h1_target / (gamma_target-1);
% h_target = h1_target + d_target
h_target = h1_target + d_target;
h2_target = h1_target + 2*d_target;
fprintf('由 h1_target & γ_target ,得到: d_target = %0.1f mm, 进而得到 h_target = %.1fmm，h2_target = %.1fmm\n\n',d_target,h_target,h2_target);

%% 计算中间变量以及弹簧长度（中&下）
rho_target = (1 - a_hat_target^2) / (gamma_target - 1)^2;
delta_hat1_target = 1 - sqrt(1 + 2*sqrt(1 - a_hat_target^2)*sqrt(rho_target) + rho_target) + delta_hat_target;
delta_hat2_target = 1 - sqrt(1 + 4*sqrt(1 - a_hat_target^2)*sqrt(rho_target) + 4*rho_target) + delta_hat_target;
delta1_target = delta_hat1_target * sqrt(a_target^2 + h1_target^2);
delta2_target = delta_hat2_target * sqrt(a_target^2 + h1_target^2);

L2 = sqrt(a_target^2 + h_target^2) + delta1_target; %中
L3 = sqrt(a_target^2 + h2_target^2) + delta2_target; %下

fprintf('由 â_target & γ_target 计算得到(中间量): ρ = %.3f \n\n', rho_target);
fprintf('由 â_target & ρ_target & 预压缩 δ̂_target 计算得到: δ̂_1 = %.3f, δ̂_2 = %.3f, 此时, 预压缩δ_1 = %.1f mm, 预压缩δ_2 = %.1f mm, L2(中) = %.1f mm, L3(下) = %.1f mm\n\n',delta_hat1_target, delta_hat2_target, delta1_target, delta2_target, L2, L3);

%% 根据1.229(paper)和load mass计算K2
k2 = (M*g)/(1.229*sqrt((a_target/1000)^2+(h1_target/1000)^2)); %N/m

%% 由 α 和 α₁ 计算 k2, k3
%% N*springs
N=1.5;
% k1 = k₂ · α_target
k1 = (k2 * alpha_target)/N;
% k₃ = α₁_target · k₂
k3 = (alpha1_target * k2)/N;
fprintf('最佳的刚度系数，上&下：k1=%0.1fN/m, 底部弹簧：k2=%0.1fN/m, 中：k3=%0.1fN/m\n\n',k1,k2,k3);

%% 计算K2的预压缩量（fig.(c)）
f1 = -(k1/1000)*delta_target*(h1_target/sqrt(a_target^2+h1_target^2));
f3 = -(k3/1000)*delta1_target*(h_target/sqrt(a_target^2+h_target^2));
f4 = -(k1/1000)*delta2_target*(h2_target/sqrt(a_target^2+h2_target^2));

f2 = -(2*f1 + 2*f3 +2*f4);
delta3_target = f2/(k2/1000); %mm %K2

fprintf('预压缩量 上：delta_target=%.1fmm, 中：delta1_target=%.1fmm, 下：delta2_target=%.1fmm, 底部：delta3_target =%.1fmm\n\n',delta_target,delta1_target,delta2_target,delta3_target);
L = h2_target + delta3_target; %底部弹簧的长度
fprintf('由预压缩计算底部弹簧的原长：L=%0.1fmm，上：L1=%0.1fmm，中：L2=%0.1fmm，下：L3=%0.1fmm\n\n',L,L1,L2,L3);
fprintf('预压缩后弹簧的长度：底部：%.1fmm, 上：%.1fmm, 中：%.1fmm, 下：%.1fmm\n\n',L-delta3_target,L1-delta_target,L2-delta1_target,L3-delta2_target);

%% 平衡时的压缩量（fig.(d)）
delta_eq = L1 - sqrt(a_target^2 + d_target^2); %mm %上&下
delta1_eq = L2 - a_target; %中
delta3_eq = (M*g)/(k2/1000); %平衡时底部弹簧的压缩量
fprintf('平衡时的压缩量：上&下：delta_eq=delta2_eq=%0.1fmm, 中：delta1_eq=%0.1fmm, 底部：delta3_eq=%0.1fmm\n\n',delta_eq,delta1_eq,delta3_eq);

L_eq = d_target + delta3_eq + delta3_target; %底部弹簧的长度
fprintf('平衡时计算底部弹簧的原长：L_eq=%0.1fmm\n\n',L_eq);
fprintf('平衡时弹簧的长度：底部：%.1fmm, 上：%.1fmm, 中：%.1fmm, 下：%.1fmm\n\n',L-delta3_eq,L1-delta_eq,L2-delta1_eq,L3-delta_eq);

y_hat = linspace(-10, 10, 1000);

%% 存储弹簧参数到Excel
%path = '/Users/caohuaqi/Desktop';
path = 'C:\Users\Administrator\Desktop';
excel_filename = fullfile(path, 'Spring_Parameters_0.5ratio_2kg_45mm_304.xlsx');

% 存储K2弹簧参数
k2_results = [];
for C = C_range
    a=(G*ratio)/(8*(C^4)*(k2/1000));
    D=(-2/C+sqrt(4/(C^2)+4*a*L))/(2*a); %2d -2/C+sqrt(4/(C^2)需要修改
    d = D/C; %K2
    D_out = D+d; %弹簧外径
    K = (4*C-1)/(4*C-4)+0.615/C; %K2
    d_target = 1.6*sqrt(K*C*M*g/tau_p);  %mm K2
    %if d >= d_target1
    n = (G*D)/(8*(C^4)*(k2/1000)); %K2 %有效圈数
    %% 用于检验
    k2_actual = (G*D)/(8*(C^4)*n); %N/mm
    p = ratio * D;
    %n_test = (L-2*d)/p;
    %fprintf('n=%0.1f\n,n=%0.1f\n\n',n,n_test);
    k2_results = [k2_results; d_target,d,D,D_out,C,n,ratio,p,G,L,k2_actual*1000];
    %fprintf('d_target =%0.1fmm,d=%0.1fmm,D=%0.1fmm,D_out=%0.1fmm,C=%0.1f,n=%0.1f,ratio=%0.1f,p=%0.1fmm,G=%0.1fMpa,L=%0.1fmm,k2_actual=%0.1fN/m\n\n',d_target,d,D,D_out,C,n,ratio,p,G,L,k2_actual*1000);
    %end
end

k2_table = array2table(k2_results, 'VariableNames', {'d_target_mm', 'd_mm', 'D_mm','D_out_mm','C', 'n', 'ratio', 'p_mm', 'G_Mpa', 'L_mm', 'k_actual_N/m'});
[~, ia] = unique(k2_table(:, {'C', 'ratio'}), 'rows');
k2_table = k2_table(ia, :);

%%如果K2变成拉簧
%%190mm为MXC上方的距离
L_k2 = 190-delta3_eq; %此时K2的原长/尼龙绳+弹簧的原长
fprintf('L_k2=%0.1fmm\n',L_k2);

% 存储K2弹簧参数——拉簧
k2_results = [];
for C = C_range
    a=(G*ratio)/(8*(C^4)*(k2/1000));
    D=(-2/C+sqrt(4/(C^2)+4*a*L_k2))/(2*a); %2d -2/C+sqrt(4/(C^2)需要修改 %%更改这里的L
    d = D/C; %K2
    D_out = D+d; %弹簧外径
    K = (4*C-1)/(4*C-4)+0.615/C; %K2
    d_target = 1.6*sqrt(K*C*M*g/tau_p);  %mm K2
    %if d >= d_target1
    n = (G*D)/(8*(C^4)*(k2/1000)); %K2 %有效圈数
    %% 用于检验
    k2_actual = (G*D)/(8*(C^4)*n); %N/mm
    p = ratio * D;
    %n_test = (L-2*d)/p;
    %fprintf('n=%0.1f\n,n=%0.1f\n\n',n,n_test);
    k2_results = [k2_results; d_target,d,D,D_out,C,n,ratio,p,G,L_k2,k2_actual*1000];
    %fprintf('d_target =%0.1fmm,d=%0.1fmm,D=%0.1fmm,D_out=%0.1fmm,C=%0.1f,n=%0.1f,ratio=%0.1f,p=%0.1fmm,G=%0.1fMpa,L=%0.1fmm,k2_actual=%0.1fN/m\n\n',d_target,d,D,D_out,C,n,ratio,p,G,L,k2_actual*1000);
    %end
end

k2_table = array2table(k2_results, 'VariableNames', {'d_target_mm', 'd_mm', 'D_mm','D_out_mm','C', 'n', 'ratio', 'p_mm', 'G_Mpa', 'L_mm', 'k_actual_N/m'});
[~, ia] = unique(k2_table(:, {'C', 'ratio'}), 'rows');
k2_table = k2_table(ia, :);

%% 上&下弹簧
k1_results = [];
for C1 = C1_range
    a1=(G*ratio1)/(8*(C1^4)*(k1/1000));
    D1=(-2/C1+sqrt(4/(C1^2)+4*a1*L1))/(2*a1);
    d1 = D1/C1; %K2
    D_out1 = D1 + d1; %弹簧外径
    K1 = (4*C1-1)/(4*C1-4)+0.615/C1; %上&下
    d_target1 = 1.6*sqrt(K1*C1*M1*g/tau_p); %mm 上&下

    %if d1 >= d1_target
    n1 = (G*D1)/(8*(C1^4)*(k1/1000)); %上&下（转换为N/mm）
    %% 用于检验
    k1_actual = (G*D1)/(8*(C1^4)*n1); %N/mm
    p1 = ratio1 * D1;
    %fprintf('d_target1 =%0.1fmm,d1=%0.1fmm,D1=%0.1fmm,D_out1=%0.1f,C1=%0.1f,n1=%0.1f,ratio1=%0.1f,p1=%0.1fmm,G=%0.1fMpa,L1=%0.1fmm,k1_actual=%0.1fN/m\n\n',d_target1,d1,D1,D_out1,C1,n1,ratio1,p1,G,L1,k1_actual*1000);
    k1_results = [k1_results; d_target1,d1,D1,D_out1,C1,n1,ratio1,p1,G,L1,k1_actual*1000];
    %end
end

k1_table = array2table(k1_results, 'VariableNames', {'d_target_mm', 'd_mm', 'D_mm','D_out_mm', 'C', 'n', 'ratio', 'p_mm', 'G_Mpa', 'L_mm', 'k_actual_N/m'});
[~, ia] = unique(k1_table(:, {'C', 'ratio'}), 'rows');
k1_table = k1_table(ia, :);

%% 存储中间弹簧参数（侧边）
k3_results = [];
for C2 = C2_range
    a2=(G*ratio1)/(8*(C2^4)*(k3/1000));
    D2=(-2/C2+sqrt(4/(C2^2)+4*a2*L2))/(2*a2);
    d2 = D2/C2; %K2
    D_out2 = D2 + d2;
    K2 = (4*C2-1)/(4*C2-4)+0.615/C2; %中
    d_target2 = 1.6*sqrt(K2*C2*M1*g/tau_p); %mm 中

    %if d2 >= d2_target
    n2 = (G*D2)/(8*(C2^4)*(k3/1000)); %中
    %% 用于检验
    k3_actual = (G*D2)/(8*(C2^4)*n2); %N/mm
    p2 = ratio2 * D2;
    %fprintf('d_target2 =%0.1fmm,d2=%0.1fmm,D2=%0.1fmm,D_out2=%0.1fmm,C2=%0.1f,n2=%0.1f,ratio2=%0.1f,p2=%0.1fmm,G=%0.1fMpa,L2=%0.1fmm,k3_actual=%0.1fN/m\n\n',d_target2,d2,D2,D_out2,C2,n2,ratio2,p2,G,L2,k3_actual*1000);
    k3_results = [k3_results; d_target2,d2,D2,D_out2,C2,n2,ratio2,p2,G,L2,k3_actual*1000];
    %end
end

k3_table = array2table(k3_results, 'VariableNames', {'d_target_mm', 'd_mm', 'D_mm','D_out_mm', 'C', 'n', 'ratio', 'p_mm', 'G_Mpa', 'L_mm', 'k_actual_N/m'});
[~, ia] = unique(k3_table(:, {'C', 'ratio'}), 'rows');
k3_table = k3_table(ia, :);

%% 写入Excel
writetable(k2_table, excel_filename, 'Sheet', 'K2_Spring');
writetable(k1_table, excel_filename, 'Sheet', 'Up_Down_Spring');
writetable(k3_table, excel_filename, 'Sheet', 'Middle_Spring');

