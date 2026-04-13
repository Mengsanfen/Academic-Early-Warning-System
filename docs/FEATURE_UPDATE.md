# 学业预警系统功能增强说明

## 新增功能概述

本次更新为学业预警系统新增了两个重要功能模块：

### 1. 规则权限配置（按年级/班级选择实施对象）
- 每条规则可以设置目标范围：全部学生、指定年级、指定班级
- 规则执行时只检测目标范围内的学生
- 支持多选年级和班级

### 2. 课程类型配置（必修/选修等）
- 课程管理模块，支持设置课程类型
- 课程类型包括：必修课、选修课、公共课、专业课、实践课
- 规则条件支持按课程类型筛选
- 成绩导入支持课程类型字段

---

## 数据库变更

### 新增字段

#### rules 表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| target_type | VARCHAR(20) | 目标类型: all-全部, grades-按年级, classes-按班级 |
| target_grades | JSON | 目标年级列表，如["2022级", "2023级"] |
| target_classes | JSON | 目标班级ID列表，如[1, 2, 3] |

#### courses 表
| 字段名 | 类型 | 说明 |
|--------|------|------|
| course_type | VARCHAR(20) | 课程类型: required-必修, elective-选修, public-公共, professional-专业, practice-实践 |

### 执行迁移

运行以下命令更新数据库：

```bash
cd backend
python migrations/add_rule_target_and_course_type.py
```

---

## API 变更

### 新增接口

#### 规则管理 (/api/v1/rules)
- `GET /rules/grades` - 获取所有年级列表
- `GET /rules/target-options` - 获取规则目标选项（年级和班级列表）

#### 课程管理 (/api/v1/courses) - 新模块
- `GET /courses` - 获取课程列表（分页）
- `GET /courses/all` - 获取所有课程（不分页）
- `GET /courses/{id}` - 获取课程详情
- `POST /courses` - 创建课程
- `PUT /courses/{id}` - 更新课程
- `PUT /courses/batch/type` - 批量更新课程类型
- `DELETE /courses/{id}` - 删除课程
- `GET /courses/semesters` - 获取学期列表
- `GET /courses/types` - 获取课程类型列表
- `GET /courses/statistics` - 获取课程统计

### 修改接口

#### 规则管理
- 创建/更新规则时支持 `target_type`, `target_grades`, `target_classes` 字段
- 规则响应中包含目标范围信息

#### 成绩管理
- 成绩列表返回 `course_type` 字段
- 课程列表返回 `course_type` 字段
- 新增 `GET /scores/course-types` 获取课程类型列表

#### 数据导入
- 成绩导入支持 `课程类型` 列
- 导入模板新增课程类型列

---

## 前端变更

### 新增页面
- 课程管理页面 (`/courses`) - 仅管理员可访问

### 修改页面
- 规则配置页面新增目标范围选择
- 规则条件配置新增课程类型筛选

### 新增路由
```typescript
{
  path: 'courses',
  name: 'Courses',
  component: () => import('@/views/courses/index.vue'),
  meta: { title: '课程管理', icon: 'Reading', roles: ['admin'] }
}
```

---

## 使用说明

### 1. 配置课程类型

1. 进入「课程管理」页面
2. 查看现有课程列表
3. 可以：
   - 单个编辑课程的类型
   - 批量选择课程后点击「批量修改类型」

### 2. 配置规则目标范围

1. 进入「规则配置」页面
2. 创建或编辑规则
3. 在「实施对象」区域：
   - 选择「全部学生」：规则适用于所有学生
   - 选择「按年级」：选择适用的年级（可多选）
   - 选择「按班级」：选择适用的班级（可多选）

### 3. 配置规则条件（按课程类型）

在规则条件配置中，可以指定课程类型筛选：
- 不选择：适用于所有课程
- 选择必修课：只统计必修课成绩
- 选择选修课：只统计选修课成绩
- 等等...

### 4. 导入成绩时设置课程类型

在成绩导入Excel中，可以添加「课程类型」列：
- 必修 / 必修课 / required
- 选修 / 选修课 / elective
- 公共 / 公共课 / public
- 专业 / 专业课 / professional
- 实践 / 实践课 / practice

---

## 典型应用场景

### 场景1：不同年级不同预警标准
- 为大一设置较宽松的挂科预警（如挂科3门预警）
- 为大四设置较严格的挂科预警（如挂科2门预警）
- 分别创建两条规则，选择不同的年级

### 场景2：必修课和选修课分别预警
- 创建「必修课挂科预警」规则，课程类型选择「必修课」
- 创建「选修课学分不足预警」规则，课程类型选择「选修课」
- 可以设置不同的阈值

### 场景3：特定班级重点关注
- 对实验班设置更高的学业要求
- 创建规则时选择特定班级
- 规则只对这些班级的学生生效

---

## 文件变更清单

### 后端
```
backend/
├── app/
│   ├── models/
│   │   ├── rule.py          # 新增 TargetType 枚举和目标范围字段
│   │   └── course.py        # 新增 CourseType 枚举和 course_type 字段
│   ├── api/v1/
│   │   ├── rules_secure.py  # 新增目标范围API
│   │   ├── courses.py       # 新增课程管理API
│   │   ├── scores_secure.py # 新增课程类型返回
│   │   ├── import_export.py # 导入支持课程类型
│   │   └── router.py        # 注册课程路由
│   └── core/rule_engine/
│       └── simple_engine.py # 支持目标范围筛选和课程类型筛选
└── migrations/
    └── add_rule_target_and_course_type.py  # 数据库迁移脚本
```

### 前端
```
frontend_new/
├── src/
│   ├── api/
│   │   ├── rule.ts          # 新增目标选项API
│   │   └── course.ts        # 新增课程管理API
│   ├── types/
│   │   └── index.ts         # 新增 TargetType, CourseType 类型
│   ├── views/
│   │   ├── rules/
│   │   │   └── index.vue    # 新增目标范围选择
│   │   └── courses/
│   │       └── index.vue    # 新增课程管理页面
│   └── router/
│       └── index.ts         # 新增课程管理路由
```

---

## 注意事项

1. **数据库迁移**：部署前请先执行数据库迁移脚本
2. **现有数据**：现有课程默认设置为「必修课」
3. **现有规则**：现有规则默认目标范围为「全部学生」
4. **权限控制**：课程管理页面仅管理员可访问
5. **兼容性**：规则条件中的 course_type 为可选字段，不影响现有规则
