<<<<<<< HEAD
=======
任务一：修复致命漏洞 —— 辅导员数据越权拦截
这个提示词将彻底解决“辅导员看到全校学生”的安全漏洞。

🤖 复制以下提示词发给 AI：

你现在是一位顶尖的高校系统架构师和 Python/FastAPI 后端专家。
我的学业预警系统目前存在“水平越权漏洞”：辅导员（role='counselor'）登录后，请求学生列表 /api/v1/students 和预警列表 /api/v1/alerts 时，查到了全校的数据。

请帮我完美修复这个漏洞，具体要求如下：

数据模型扩展：假设辅导员管理特定的班级。请在已有的 User 或关联表中增加字段（如 managed_class_ids，或者通过多对多关系），以确定当前辅导员管理哪些 class_id。

重写查询接口：请重写获取学生列表和预警列表的 GET 接口。必须通过 Depends 获取 current_user。

核心拦截逻辑：

如果 current_user.role == 'admin'，执行 query.all() 返回全量数据。

如果 current_user.role == 'counselor'，获取其管理的 class_id 列表，在 SQLAlchemy 查询中使用 .filter(Student.class_id.in_(管理的班级列表)) 进行强拦截。

对于 alerts 预警列表，同理，需要 join 学生表后使用班级 ID 拦截。

请给出修改后的数据模型定义和两个完整路由接口的 Python 代码，确保代码健壮，处理好空值异常。

【附上我的真实模型代码，请严格基于此字段名修改：】
（在这里粘贴你的 models.py）

任务二：增加业务亮点 —— 学生申诉与双向互动
这个提示词将把你的系统从“单向通知工具”升级为“人性化双向互动平台”。

🤖 复制以下提示词发给 AI：

作为一名前端架构师和全栈专家，请帮我完善学业预警系统中的“双向互动”功能。
目前学生端查看“预警详情”只是单向展示，我需要增加“学生申诉/反馈”功能。

请给出前后端协同的完整实现代码，要求如下：

后端 (FastAPI)：在 Alert 模型中新增两个字段：student_feedback (TEXT，记录学生填写的申诉内容) 和 feedback_time (DATETIME)。并新增一个接口 POST /api/v1/alerts/{alert_id}/feedback 供学生提交反馈。

前端 (Vue3 + Element Plus)：修改学生端的预警详情弹窗组件。

在弹窗底部增加一个 <el-input type="textarea"> 供学生填写反馈说明（例如：“老师，我上周是因为生病住院才缺勤的”）。

增加一个“提交反馈”按钮。如果该条预警已经提交过反馈，则禁用输入框和按钮，并显示已填写的反馈内容。

辅导员端联动：辅导员查看该预警时，在详情里必须能看到学生刚刚填写的 student_feedback 内容。

请给出后端新增接口代码和 Vue3 的核心模板及 script setup 逻辑。

任务三：点亮毕设题目 —— 多源数据综合风险判定
这是答辩老师最关心的核心技术。不要让系统只能查单一的挂科或缺勤。

🤖 复制以下提示词发给 AI：

作为资深后端架构师，我的毕设题目叫做“基于多源数据与规则引擎的学业预警系统”。目前我的系统只能进行单一维度（单看成绩，或单看考勤）的预警判断，偏离了“多源数据”的核心。

请帮我扩展现有的 Python RuleEngine（规则引擎）逻辑，实现跨维度的**“综合学业风险判定”**。要求如下：

设计一条名为 COMPREHENSIVE_RISK（学业综合风险）的复合规则逻辑。

触发条件（必须同时满足两项数据源）：学生“单学期不及格课程数 >= 2门” 并且（AND） “累计缺勤次数 >= 3次”。

核心代码重写：请写一个单独的 evaluate_comprehensive_rule(student_id, db_session) 函数。在这个函数中，同时查询该学生的 Score（成绩源）和 Attendance（考勤源）。

使用 Python 原生逻辑进行判断，如果同时达标，则在 Alert 表中生成一条级别为“紧急(Urgent)”的预警记录。

提示语（message）需要拼接多源数据，例如：“综合风险：该生已挂科 2 门，且缺勤 3 次，请立即干预！”。

请给我可以在 FastAPI 项目中直接调用的完整逻辑代码。

任务四：商业级产品包装 —— 一键导出预警报表 (Excel)
有了这个功能，系统的实用价值和逼格会瞬间拉满。

🤖 复制以下提示词发给 AI：

请帮我的 Vue3 + FastAPI 管理后台实现一个实用的商业级功能：导出预警数据为 Excel 报表。

需求细节：

后端接口设计：编写一个 GET /api/v1/alerts/export 接口。使用 pandas 或者 openpyxl 库，查询出当前条件下的预警记录。

需要导出的列包括：学号、姓名、班级、预警规则、预警级别、生成时间、当前状态。

使用 FastAPI 的 StreamingResponse 或 FileResponse 将生成的 Excel 流返回给前端，设置正确的响应头（application/vnd.openxmlformats-officedocument.spreadsheetml.sheet）。

前端下载逻辑：在预警中心列表页右上角增加一个 <el-button type="success" icon="Download">导出报表</el-button>。

前端 API 请求：请使用 axios 编写处理文件流下载的函数，要求设置 responseType: 'blob'，并使用动态创建 <a> 标签的方式触发浏览器下载，文件命名为 学业预警报表_{当前日期}.xlsx。

请给出后端的完整生成与返回逻辑，以及前端按钮点击后的下载处理函数。
>>>>>>> fae0ad2022f3d7ffd137ac93f59901d4146ab13a
