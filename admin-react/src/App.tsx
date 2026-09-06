import React, { useState, useEffect } from 'react'
import { Layout, Menu, Card, Row, Col, Statistic, Table, Tag, Button, Space, Modal, Form, Input, Select, message, Empty, Spin } from 'antd'
import { UserOutlined, BarChartOutlined, RadarChartOutlined, ExceptionOutlined, DashboardOutlined, LogoutOutlined, MenuFoldOutlined, MenuUnfoldOutlined, FileTextOutlined } from '@ant-design/icons'
import * as echarts from 'echarts'
import axios from 'axios'
import './App.css'

const { Header, Sider, Content } = Layout

interface DashboardStats {
  total_users: number
  active_users: number
  new_today: number
  total_messages: number
  total_stickers: number
  total_voices: number
}

interface User {
  id: number
  username: string
  gender: string
  created_at: string
  is_active: boolean
}

interface SystemMetrics {
  status: string
  db_status: string
  cpu_percent: number
  memory_percent: number
  disk_percent: number
  memory_used: string
  memory_total: string
  timestamp: string
}

interface Exception {
  id: number
  type: string
  message: string
  created_at: string
  count: number
}

interface MenuItem {
  key: string
  label: string
  icon: React.ReactNode
}

const App: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false)
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [token, setToken] = useState(localStorage.getItem('admin_token') || '')
  const [username, setUsername] = useState(localStorage.getItem('admin_username') || '')
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [users, setUsers] = useState<User[]>([])
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null)
  const [exceptions, setExceptions] = useState<Exception[]>([])
  const [logs, setLogs] = useState<any[]>([])
  const [permissions, setPermissions] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [showLoginModal, setShowLoginModal] = useState(!token)
  const [form] = Form.useForm()
  const [userForm] = Form.useForm()
  const [showUserModal, setShowUserModal] = useState(false)
  const [editingUser, setEditingUser] = useState<any>(null)
  const [isCreating, setIsCreating] = useState(false)

  // 初始化图表
  const initChart = (chartId: string, option: any) => {
    const chartDom = document.getElementById(chartId)
    if (chartDom) {
      const myChart = echarts.init(chartDom)
      myChart.setOption(option)
      window.addEventListener('resize', () => myChart.resize())
    }
  }

  // 获取统计数据
  const fetchStats = async (authToken: string) => {
    try {
      setLoading(true)
      const response = await axios.get('/api/admin/analytics/dashboard', {
        headers: { Authorization: `Bearer ${authToken}` }
      })
      setStats(response.data.data || response.data)
      setTimeout(() => initDashboardCharts(), 100)
    } catch (error) {
      message.error('获取统计数据失败')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  // 获取用户列表
  const fetchUsers = async (authToken: string) => {
    try {
      setLoading(true)
      const response = await axios.get('/api/admin/users', {
        headers: { Authorization: `Bearer ${authToken}` }
      })
      setUsers(response.data.data || [])
    } catch (error) {
      message.error('获取用户列表失败')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  // 获取消息分析
  const fetchMessages = async (authToken: string) => {
    try {
      const response = await axios.get('/api/admin/analytics/messages', {
        headers: { Authorization: `Bearer ${authToken}` }
      })
      setTimeout(() => initMessageCharts(response.data), 100)
    } catch (error) {
      console.error(error)
    }
  }

  // 获取系统监控
  const fetchMetrics = async (authToken: string) => {
    try {
      const response = await axios.get('/api/admin/monitoring/system', {
        headers: { Authorization: `Bearer ${authToken}` }
      })
      setMetrics(response.data)
      setTimeout(() => initMonitoringCharts(response.data), 100)
    } catch (error) {
      console.error(error)
    }
  }

  // 获取异常日志
  const fetchExceptions = async (authToken: string) => {
    try {
      const response = await axios.get('/api/admin/exceptions/list', {
        headers: { Authorization: `Bearer ${authToken}` }
      })
      setExceptions(response.data.exceptions || [])
      setTimeout(() => initExceptionCharts(response.data), 100)
    } catch (error) {
      console.error(error)
    }
  }

  // 获取系统日志
  const fetchLogs = async (authToken: string) => {
    try {
      setLoading(true)
      const response = await axios.get('/api/admin/logs', {
        headers: { Authorization: `Bearer ${authToken}` }
      })
      setLogs(response.data.data || [])
    } catch (error) {
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  // 获取高级分析数据
  const fetchAdvancedAnalytics = async (authToken: string) => {
    try {
      setLoading(true)
      const response = await axios.get('/api/admin/analytics/advanced', {
        headers: { Authorization: `Bearer ${authToken}` }
      })
      setTimeout(() => initAdvancedCharts(response.data), 100)
    } catch (error) {
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  // 获取权限和角色信息
  const fetchPermissions = async (authToken: string) => {
    try {
      setLoading(true)
      const response = await axios.get('/api/admin/permissions', {
        headers: { Authorization: `Bearer ${authToken}` }
      })
      setPermissions(response.data)
    } catch (error) {
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  // 初始化仪表盘图表
  const initDashboardCharts = () => {
    // 消息趋势图
    const messageTrendOption = {
      title: { text: '消息趋势', left: 'center' },
      tooltip: { trigger: 'axis' },
      grid: { top: 50, right: 30, bottom: 30, left: 60 },
      xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] },
      yAxis: { type: 'value' },
      series: [{
        data: [120, 132, 101, 134, 90, 230, 210],
        type: 'line',
        smooth: true,
        itemStyle: { color: '#1890ff' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(24, 144, 255, 0.3)' },
          { offset: 1, color: 'rgba(24, 144, 255, 0)' }
        ])}
      }]
    }
    initChart('messageTrendChart', messageTrendOption)

    // 表情包分布
    const stickerDistOption = {
      title: { text: '表情包分布', left: 'center' },
      tooltip: { trigger: 'item' },
      series: [{
        data: [
          { value: 8, name: '开心' },
          { value: 7, name: '难过' },
          { value: 6, name: '生气' },
          { value: 9, name: '平静' },
          { value: 9, name: '爱意' },
          { value: 4, name: '温柔' }
        ],
        type: 'pie',
        radius: ['40%', '70%']
      }]
    }
    initChart('stickerDistChart', stickerDistOption)

    // 角色排行
    const topSoulsOption = {
      title: { text: '角色排行', left: 'center' },
      tooltip: { trigger: 'axis' },
      grid: { top: 50, right: 30, bottom: 30, left: 60 },
      xAxis: { type: 'category', data: ['Luna', 'Aria', 'Caelus', 'Raven', 'Diana', 'Elara'] },
      yAxis: { type: 'value' },
      series: [{
        data: [120, 100, 95, 88, 75, 70],
        type: 'bar',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#83bff6' },
            { offset: 0.5, color: '#188df0' },
            { offset: 1, color: '#188df0' }
          ])
        }
      }]
    }
    initChart('topSoulsChart', topSoulsOption)
  }

  // 消息分析图表
  const initMessageCharts = (data: any) => {
    const dailyData = data.daily || []
    const dates = dailyData.map((d: any) => d.date?.slice(5) || '')
    const counts = dailyData.map((d: any) => d.count || 0)

    const option = {
      title: { text: '消息每日分布', left: 'center' },
      tooltip: { trigger: 'axis' },
      grid: { top: 50, right: 30, bottom: 30, left: 60 },
      xAxis: { type: 'category', data: dates.length ? dates : ['无数据'] },
      yAxis: { type: 'value' },
      series: [{
        data: counts.length ? counts : [0],
        type: 'bar',
        itemStyle: { color: '#52c41a' }
      }]
    }
    initChart('messageDailyChart', option)

    // 表情包使用分析
    const stickerOption = {
      title: { text: '表情包使用', left: 'center' },
      tooltip: { trigger: 'item' },
      series: [{
        data: data.stickers || [
          { value: 15, name: '开心' },
          { value: 12, name: '难过' },
          { value: 10, name: '生气' }
        ],
        type: 'pie'
      }]
    }
    initChart('stickerUsageChart', stickerOption)

    // 用户活跃度
    const activityData = data.user_activity || []
    const activityDates = activityData.map((d: any) => d.date?.slice(5) || '')
    const activityCounts = activityData.map((d: any) => d.active_count || 0)

    const activityOption = {
      title: { text: '用户活跃度', left: 'center' },
      tooltip: { trigger: 'axis' },
      grid: { top: 50, right: 30, bottom: 30, left: 60 },
      xAxis: { type: 'category', data: activityDates },
      yAxis: { type: 'value' },
      series: [{
        data: activityCounts,
        type: 'line',
        smooth: true,
        itemStyle: { color: '#1890ff' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(24, 144, 255, 0.3)' },
          { offset: 1, color: 'rgba(24, 144, 255, 0)' }
        ])}
      }]
    }
    initChart('userActivityChart', activityOption)

    // 聊天频率分布
    const freqData = data.chat_frequency || []
    const freqHours = freqData.map((d: any) => d.hour)
    const freqCounts = freqData.map((d: any) => d.count)

    const freqOption = {
      title: { text: '聊天频率分布 (小时)', left: 'center' },
      tooltip: { trigger: 'axis' },
      grid: { top: 50, right: 30, bottom: 30, left: 60 },
      xAxis: { type: 'category', data: freqHours },
      yAxis: { type: 'value' },
      series: [{
        data: freqCounts,
        type: 'line',
        smooth: true,
        itemStyle: { color: '#fa8c16' }
      }]
    }
    initChart('chatFrequencyChart', freqOption)

    // 消息情绪分析
    const sentimentData = data.message_sentiment || []
    const sentimentOption = {
      title: { text: '消息情绪分析', left: 'center' },
      tooltip: { trigger: 'item' },
      series: [{
        data: sentimentData.map((d: any) => ({
          value: d.count,
          name: d.sentiment === 'positive' ? '积极' : d.sentiment === 'neutral' ? '中立' : '消极'
        })),
        type: 'pie',
        radius: ['40%', '70%']
      }]
    }
    initChart('sentimentChart', sentimentOption)

    // 角色排行
    const souls = data.top_souls || []
    const soulNames = souls.map((s: any) => s.name)
    const soulCounts = souls.map((s: any) => s.count)

    const soulOption = {
      title: { text: '角色排行', left: 'center' },
      tooltip: { trigger: 'axis' },
      grid: { top: 50, right: 30, bottom: 30, left: 60 },
      xAxis: { type: 'category', data: soulNames },
      yAxis: { type: 'value' },
      series: [{
        data: soulCounts,
        type: 'bar',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#83bff6' },
            { offset: 0.5, color: '#188eef' },
            { offset: 1, color: '#188eef' }
          ])
        }
      }]
    }
    initChart('topSoulsChart', soulOption)
  }

  // 系统监控图表
  const initMonitoringCharts = (data: SystemMetrics) => {
    const metrics = [
      { name: 'CPU', value: data.cpu_percent, color: '#ff4d4f' },
      { name: '内存', value: data.memory_percent, color: '#faad14' },
      { name: '磁盘', value: data.disk_percent, color: '#1890ff' }
    ]

    metrics.forEach((metric, idx) => {
      const chartId = `gauge${idx}`
      const dom = document.getElementById(chartId)
      if (dom) {
        const chart = echarts.init(dom)
        const option = {
          series: [{
            type: 'gauge',
            startAngle: 200,
            endAngle: -20,
            min: 0,
            max: 100,
            splitNumber: 10,
            axisLine: {
              lineStyle: {
                width: 30,
                color: [[0.3, '#91d5ff'], [0.7, '#1890ff'], [1, '#ff4d4f']]
              }
            },
            pointer: { itemStyle: { color: 'auto' } },
            axisTick: { distance: 50, splitNumber: 5 },
            splitLine: { distance: 50, length: 8 },
            axisLabel: { color: 'auto', distance: 80 },
            detail: { valueAnimation: true, formatter: '{value}%', color: 'auto' },
            data: [{ value: Math.round(metric.value), name: metric.name }]
          }]
        }
        chart.setOption(option)
      }
    })
  }

  // 异常趋势图表
  const initExceptionCharts = (data: any) => {
    const trendData = data.trend || []
    const dates = trendData.map((d: any) => d.date?.slice(5) || '')
    const counts = trendData.map((d: any) => d.count || 0)

    const option = {
      title: { text: '异常趋势', left: 'center' },
      tooltip: { trigger: 'axis' },
      grid: { top: 50, right: 30, bottom: 30, left: 60 },
      xAxis: { type: 'category', data: dates.length ? dates : ['无数据'] },
      yAxis: { type: 'value' },
      series: [{
        data: counts.length ? counts : [0],
        type: 'line',
        smooth: true,
        itemStyle: { color: '#ff4d4f' }
      }]
    }
    initChart('exceptionTrendChart', option)

    // 异常分类分布
    const distOption = {
      title: { text: '异常分类', left: 'center' },
      tooltip: { trigger: 'item' },
      series: [{
        data: data.exceptions?.slice(0, 5).map((e: any) => ({ value: e.count, name: e.type })) || [],
        type: 'pie'
      }]
    }
    initChart('exceptionDistChart', distOption)
  }

  // 高级分析图表
  const initAdvancedCharts = (data: any) => {
    // 热力图：用户活动时间分布
    const heatmapData = (data.heatmap_data || []).map((d: any) => [d.day, d.hour, d.value])
    const heatmapOption = {
      title: { text: '用户活动热力图（时间分布）', left: 'center' },
      tooltip: { trigger: 'item' },
      grid: { top: 50, right: 30, bottom: 30, left: 60 },
      xAxis: { type: 'category', data: Array.from({ length: 7 }, (_, i) => `周${i}`) },
      yAxis: { type: 'category', data: Array.from({ length: 24 }, (_, i) => `${i}:00`) },
      visualMap: { min: 0, max: 30, orient: 'vertical', right: 10, top: 50 },
      series: [{
        data: heatmapData,
        type: 'heatmap',
        itemStyle: { borderRadius: 3 }
      }]
    }
    initChart('heatmapChart', heatmapOption)

    // 漏斗图：用户转化流程
    const funnelData = data.funnel_data || []
    const funnelOption = {
      title: { text: '用户转化漏斗', left: 'center' },
      tooltip: { trigger: 'item' },
      series: [{
        data: funnelData.map((d: any) => ({ value: d.count, name: d.stage })),
        type: 'funnel',
        left: '10%',
        top: 50,
        bottom: 50,
        width: '80%',
        min: 0,
        max: 1000,
        minSize: '50%',
        maxSize: '100%',
        sort: 'descending',
        gap: 2,
        itemStyle: {
          borderColor: '#fff',
          borderWidth: 1
        },
        emphasis: {
          label: { fontSize: 13 }
        },
        label: {
          formatter: '{b}: {c}'
        },
        labelLine: {
          length: 20,
          lineStyle: {
            width: 1,
            type: 'solid'
          }
        }
      }]
    }
    initChart('funnelChart', funnelOption)

    // 散点图：用户活跃度分析
    const scatterData = data.scatter_data || []
    const scatterOption = {
      title: { text: '用户活跃度分析', left: 'center' },
      tooltip: { trigger: 'item', formatter: '{a}: ({c[0]}, {c[1]})' },
      grid: { top: 50, right: 30, bottom: 30, left: 60 },
      xAxis: { type: 'value', name: '活跃度', min: 0, max: 500 },
      yAxis: { type: 'value', name: '消息数', min: 0, max: 300 },
      series: [{
        data: scatterData.map((d: any) => [d.x, d.y, d.size]),
        type: 'scatter',
        symbolSize: (data: any) => data[2] / 3,
        itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 1, [
          { offset: 0, color: '#83bff6' },
          { offset: 0.5, color: '#188eef' },
          { offset: 1, color: '#188eef' }
        ])}
      }]
    }
    initChart('scatterChart', scatterOption)

    // 树状图：角色分布
    const treeData = data.tree_data || {}
    const treeOption = {
      title: { text: '角色用户分布树', left: 'center' },
      tooltip: { trigger: 'item' },
      series: [{
        data: [treeData],
        type: 'treemap',
        label: { show: true },
        itemStyle: {
          gapWidth: 2
        }
      }]
    }
    initChart('treeChart', treeOption)
  }

  // 处理登录
  const handleLogin = async (values: { username: string; password: string }) => {
    try {
      const response = await axios.post('/api/auth/login', values)
      const { token } = response.data
      setToken(token)
      setUsername(values.username)
      localStorage.setItem('admin_token', token)
      localStorage.setItem('admin_username', values.username)
      setShowLoginModal(false)
      message.success('登录成功')
      fetchStats(token)
    } catch (error) {
      message.error('登录失败，账号或密码错误')
    }
  }

  // 处理登出
  const handleLogout = () => {
    setToken('')
    setUsername('')
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_username')
    setShowLoginModal(true)
    setCurrentPage('dashboard')
  }

  // 创建/编辑用户
  const handleEditUser = (user: any) => {
    setEditingUser(user)
    setIsCreating(false)
    userForm.setFieldsValue({
      username: user.username,
      gender: user.gender,
      nickname: user.nickname
    })
    setShowUserModal(true)
  }

  const handleCreateUser = () => {
    setEditingUser(null)
    setIsCreating(true)
    userForm.resetFields()
    setShowUserModal(true)
  }

  const handleSaveUser = async (values: any) => {
    try {
      if (isCreating) {
        await axios.post('/api/admin/users', values, {
          headers: { Authorization: `Bearer ${token}` }
        })
        message.success('用户创建成功')
      } else {
        await axios.put(`/api/admin/users/${editingUser.id}`, values, {
          headers: { Authorization: `Bearer ${token}` }
        })
        message.success('用户更新成功')
      }
      setShowUserModal(false)
      fetchUsers(token)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败')
    }
  }

  const handleDeleteUser = (userId: string) => {
    Modal.confirm({
      title: '删除用户',
      content: '确认要删除该用户吗？（仅标记停用）',
      onOk: async () => {
        try {
          await axios.delete(`/api/admin/users/${userId}`, {
            headers: { Authorization: `Bearer ${token}` }
          })
          message.success('用户已停用')
          fetchUsers(token)
        } catch (error: any) {
          message.error(error.response?.data?.detail || '删除失败')
        }
      }
    })
  }

  // 更改用户角色
  const handleChangeRole = (user: any, role: string) => {
    Modal.confirm({
      title: '更改用户角色',
      content: `确认要将 ${user.username} 的角色改为 ${role.toUpperCase()} 吗？`,
      onOk: async () => {
        try {
          await axios.put(`/api/admin/users/${user.id}/role`, { role }, {
            headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
          })
          message.success('角色已更新')
          fetchUsers(token)
        } catch (error: any) {
          message.error(error.response?.data?.detail || '更新失败')
        }
      }
    })
  }

  // 页面切换
  useEffect(() => {
    if (token) {
      switch (currentPage) {
        case 'dashboard':
          fetchStats(token)
          break
        case 'users':
          fetchUsers(token)
          break
        case 'analytics':
          fetchMessages(token)
          break
        case 'monitoring':
          fetchMetrics(token)
          break
        case 'exceptions':
          fetchExceptions(token)
          break
        case 'logs':
          fetchLogs(token)
          break
        case 'advanced_analytics':
          fetchAdvancedAnalytics(token)
          break
        case 'permissions':
          fetchPermissions(token)
          break
      }
    }
  }, [currentPage, token])

  // 用户表列
  const userColumns = [
    { title: '用户名', dataIndex: 'username', key: 'username', width: 120 },
    { title: '性别', dataIndex: 'gender', key: 'gender', width: 80 },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (is_active: boolean) => <Tag color={is_active ? 'green' : 'red'}>{is_active ? '活跃' : '停用'}</Tag>
    },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (text: string) => text?.slice(0, 10) },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: any) => (
        <Space size="small">
          <Button type="primary" size="small" onClick={() => handleEditUser(record)}>编辑</Button>
          <Button danger size="small" onClick={() => handleDeleteUser(record.id)}>删除</Button>
        </Space>
      )
    }
  ]

  // 异常表列
  const exceptionColumns = [
    { title: '异常类型', dataIndex: 'type', key: 'type', width: 120 },
    { title: '错误信息', dataIndex: 'message', key: 'message', width: 300, ellipsis: true },
    { title: '发生次数', dataIndex: 'count', key: 'count', width: 80 },
    { title: '最后时间', dataIndex: 'created_at', key: 'created_at', render: (text: string) => text?.slice(0, 10) }
  ]

  // 日志表列
  const logColumns = [
    { title: '用户', dataIndex: 'username', key: 'username', width: 100 },
    { title: '操作', dataIndex: 'action', key: 'action', width: 120 },
    { title: '目标', dataIndex: 'target', key: 'target', width: 150, ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: string) => <Tag color={status === 'success' ? 'green' : 'red'}>{status === 'success' ? '成功' : '失败'}</Tag>
    },
    { title: 'IP', dataIndex: 'ip_address', key: 'ip_address', width: 120 },
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180, render: (text: string) => text?.slice(0, 19) }
  ]

  const menuItems: MenuItem[] = [
    { key: 'dashboard', label: '仪表盘', icon: <DashboardOutlined /> },
    { key: 'users', label: '用户管理', icon: <UserOutlined /> },
    { key: 'analytics', label: '数据分析', icon: <BarChartOutlined /> },
    { key: 'advanced_analytics', label: '高级分析', icon: <BarChartOutlined /> },
    { key: 'monitoring', label: '系统监控', icon: <RadarChartOutlined /> },
    { key: 'exceptions', label: '异常日志', icon: <ExceptionOutlined /> },
    { key: 'logs', label: '操作日志', icon: <FileTextOutlined /> },
    { key: 'permissions', label: '权限管理', icon: <UserOutlined /> }
  ]

  if (showLoginModal && !token) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
        <Card style={{ width: 400, boxShadow: '0 10px 40px rgba(0, 0, 0, 0.2)' }}>
          <h1 style={{ textAlign: 'center', marginBottom: 30, fontSize: 24, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Lunaris 管理后台
          </h1>
          <Form form={form} onFinish={handleLogin} layout="vertical">
            <Form.Item name="username" label="账号" rules={[{ required: true, message: '请输入账号' }]}>
              <Input placeholder="输入用户名" />
            </Form.Item>
            <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
              <Input type="password" placeholder="输入密码" />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" style={{ width: '100%', height: 40, fontSize: 16 }} loading={loading}>
                登录
              </Button>
            </Form.Item>
          </Form>
          <div style={{ textAlign: 'center', color: '#999', fontSize: 12, marginTop: 20, borderTop: '1px solid #f0f0f0', paddingTop: 15 }}>
            <p>演示账号: <strong>admin</strong> (男) / <strong>luna</strong> (女)</p>
            <p>密码: <strong>admin123</strong> / <strong>luna123</strong></p>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed} style={{ background: '#001529' }}>
        <div style={{ color: 'white', padding: '20px', textAlign: 'center', fontSize: 20, fontWeight: 'bold', borderBottom: '1px solid #1890ff' }}>
          {!collapsed && '🌙 Lunaris'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[currentPage]}
          items={menuItems as any}
          onClick={(e) => setCurrentPage(e.key)}
          style={{ background: '#001529' }}
        />
      </Sider>

      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
          <Button type="text" size="large" icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} onClick={() => setCollapsed(!collapsed)} />
          <Space>
            <span>欢迎, <strong>{username}</strong></span>
            <Button type="primary" danger onClick={handleLogout} icon={<LogoutOutlined />}>
              登出
            </Button>
          </Space>
        </Header>

        <Content style={{ margin: '24px 16px', background: '#f5f5f5', minHeight: 'calc(100vh - 64px)' }}>
          <Spin spinning={loading}>
            {currentPage === 'dashboard' && (
              <div>
                <Row gutter={16} style={{ marginBottom: 24 }}>
                  <Col xs={24} sm={12} lg={4}>
                    <Card>
                      <Statistic title="总用户数" value={stats?.total_users || 0} prefix="👥" />
                    </Card>
                  </Col>
                  <Col xs={24} sm={12} lg={4}>
                    <Card>
                      <Statistic title="活跃用户" value={stats?.active_users || 0} prefix="✅" valueStyle={{ color: '#52c41a' }} />
                    </Card>
                  </Col>
                  <Col xs={24} sm={12} lg={4}>
                    <Card>
                      <Statistic title="今日新增" value={stats?.new_today || 0} prefix="📈" valueStyle={{ color: '#1890ff' }} />
                    </Card>
                  </Col>
                  <Col xs={24} sm={12} lg={4}>
                    <Card>
                      <Statistic title="消息数" value={stats?.total_messages || 0} prefix="💬" valueStyle={{ color: '#faad14' }} />
                    </Card>
                  </Col>
                  <Col xs={24} sm={12} lg={4}>
                    <Card>
                      <Statistic title="表情包" value={stats?.total_stickers || 0} prefix="😊" valueStyle={{ color: '#ff4d4f' }} />
                    </Card>
                  </Col>
                  <Col xs={24} sm={12} lg={4}>
                    <Card>
                      <Statistic title="语音消息" value={stats?.total_voices || 0} prefix="🎤" valueStyle={{ color: '#722ed1' }} />
                    </Card>
                  </Col>
                </Row>

                <Row gutter={16} style={{ marginBottom: 24 }}>
                  <Col xs={24} lg={12}>
                    <Card title="消息趋势">
                      <div id="messageTrendChart" style={{ height: 300 }}></div>
                    </Card>
                  </Col>
                  <Col xs={24} lg={12}>
                    <Card title="表情包分布">
                      <div id="stickerDistChart" style={{ height: 300 }}></div>
                    </Card>
                  </Col>
                </Row>

                <Card title="角色排行">
                  <div id="topSoulsChart" style={{ height: 300 }}></div>
                </Card>
              </div>
            )}

            {currentPage === 'users' && (
              <>
                <Card title="用户管理" extra={<Button type="primary" onClick={handleCreateUser}>+ 新增用户</Button>}>
                  <Table
                    columns={userColumns}
                    dataSource={users.map((u, idx) => ({ ...u, key: idx }))}
                    pagination={{ pageSize: 10 }}
                    scroll={{ x: 600 }}
                  />
                </Card>

                <Modal
                  title={isCreating ? '新增用户' : '编辑用户'}
                  open={showUserModal}
                  onOk={() => userForm.submit()}
                  onCancel={() => setShowUserModal(false)}
                >
                  <Form
                    form={userForm}
                    layout="vertical"
                    onFinish={handleSaveUser}
                  >
                    {isCreating && (
                      <>
                        <Form.Item
                          name="username"
                          label="用户名"
                          rules={[{ required: true, message: '请输入用户名' }]}
                        >
                          <Input />
                        </Form.Item>
                        <Form.Item
                          name="password"
                          label="密码"
                          rules={[{ required: true, message: '请输入密码' }]}
                        >
                          <Input type="password" />
                        </Form.Item>
                      </>
                    )}
                    {!isCreating && (
                      <Form.Item
                        name="username"
                        label="用户名"
                        rules={[{ required: true, message: '请输入用户名' }]}
                      >
                        <Input />
                      </Form.Item>
                    )}
                    <Form.Item
                      name="gender"
                      label="性别"
                      rules={[{ required: true, message: '请选择性别' }]}
                    >
                      <Select>
                        <Select.Option value="male">男</Select.Option>
                        <Select.Option value="female">女</Select.Option>
                      </Select>
                    </Form.Item>
                    <Form.Item
                      name="nickname"
                      label="昵称"
                    >
                      <Input />
                    </Form.Item>
                  </Form>
                </Modal>
              </>
            )}

            {currentPage === 'analytics' && (
              <div>
                <Row gutter={16} style={{ marginBottom: 24 }}>
                  <Col xs={24} lg={12}>
                    <Card title="消息每日分布">
                      <div id="messageDailyChart" style={{ height: 300 }}></div>
                    </Card>
                  </Col>
                  <Col xs={24} lg={12}>
                    <Card title="表情包使用">
                      <div id="stickerUsageChart" style={{ height: 300 }}></div>
                    </Card>
                  </Col>
                </Row>

                <Row gutter={16} style={{ marginBottom: 24 }}>
                  <Col xs={24} lg={12}>
                    <Card title="用户活跃度">
                      <div id="userActivityChart" style={{ height: 300 }}></div>
                    </Card>
                  </Col>
                  <Col xs={24} lg={12}>
                    <Card title="聊天频率分布">
                      <div id="chatFrequencyChart" style={{ height: 300 }}></div>
                    </Card>
                  </Col>
                </Row>

                <Row gutter={16} style={{ marginBottom: 24 }}>
                  <Col xs={24} lg={12}>
                    <Card title="消息情绪分析">
                      <div id="sentimentChart" style={{ height: 300 }}></div>
                    </Card>
                  </Col>
                  <Col xs={24} lg={12}>
                    <Card title="角色排行">
                      <div id="topSoulsChart" style={{ height: 300 }}></div>
                    </Card>
                  </Col>
                </Row>
              </div>
            )}

            {currentPage === 'monitoring' && (
              <div>
                <Row gutter={16} style={{ marginBottom: 24 }}>
                  <Col xs={24} sm={8}>
                    <Card title="CPU 使用率">
                      <div style={{ textAlign: 'center', marginBottom: 16 }}>
                        <div style={{ fontSize: 32, fontWeight: 'bold', color: metrics && metrics.cpu_percent > 80 ? '#ff4d4f' : '#1890ff' }}>
                          {metrics?.cpu_percent.toFixed(1)}%
                        </div>
                      </div>
                      <div id="gauge0" style={{ height: 200 }}></div>
                    </Card>
                  </Col>
                  <Col xs={24} sm={8}>
                    <Card title="内存使用率">
                      <div style={{ textAlign: 'center', marginBottom: 16 }}>
                        <div style={{ fontSize: 32, fontWeight: 'bold', color: metrics && metrics.memory_percent > 80 ? '#ff4d4f' : '#1890ff' }}>
                          {metrics?.memory_percent.toFixed(1)}%
                        </div>
                        <div style={{ fontSize: 12, color: '#666' }}>
                          {metrics?.memory_used} / {metrics?.memory_total}
                        </div>
                      </div>
                      <div id="gauge1" style={{ height: 200 }}></div>
                    </Card>
                  </Col>
                  <Col xs={24} sm={8}>
                    <Card title="磁盘使用率">
                      <div style={{ textAlign: 'center', marginBottom: 16 }}>
                        <div style={{ fontSize: 32, fontWeight: 'bold', color: metrics && metrics.disk_percent > 80 ? '#ff4d4f' : '#1890ff' }}>
                          {metrics?.disk_percent.toFixed(1)}%
                        </div>
                      </div>
                      <div id="gauge2" style={{ height: 200 }}></div>
                    </Card>
                  </Col>
                </Row>
                {metrics && (
                  <Card title="系统状态" style={{ marginTop: 16 }}>
                    <Row gutter={16}>
                      <Col xs={24} sm={12}>
                        <div style={{ marginBottom: 12 }}>
                          <span style={{ marginRight: 12 }}>🖥️ 系统状态：</span>
                          <Tag color={metrics.status === 'healthy' ? 'green' : 'red'}>
                            {metrics.status === 'healthy' ? '✅ 正常' : '❌ 异常'}
                          </Tag>
                        </div>
                      </Col>
                      <Col xs={24} sm={12}>
                        <div>
                          <span style={{ marginRight: 12 }}>🗄️ 数据库：</span>
                          <Tag color={metrics.db_status === 'connected' ? 'green' : 'red'}>
                            {metrics.db_status === 'connected' ? '✅ 已连接' : '❌ 未连接'}
                          </Tag>
                        </div>
                      </Col>
                    </Row>
                    <div style={{ marginTop: 16, fontSize: 12, color: '#999' }}>
                      最后更新: {new Date(metrics.timestamp).toLocaleString()}
                    </div>
                  </Card>
                )}
              </div>
            )}

            {currentPage === 'exceptions' && (
              <div>
                <Row gutter={16} style={{ marginBottom: 24 }}>
                  <Col xs={24} lg={12}>
                    <Card title="异常趋势">
                      <div id="exceptionTrendChart" style={{ height: 300 }}></div>
                    </Card>
                  </Col>
                  <Col xs={24} lg={12}>
                    <Card title="异常分类">
                      <div id="exceptionDistChart" style={{ height: 300 }}></div>
                    </Card>
                  </Col>
                </Row>

                <Card title="异常日志">
                  {exceptions.length ? (
                    <Table
                      columns={exceptionColumns}
                      dataSource={exceptions.map((e, idx) => ({ ...e, key: idx }))}
                      pagination={{ pageSize: 10 }}
                      scroll={{ x: 800 }}
                    />
                  ) : (
                    <Empty description="暂无异常数据" />
                  )}
                </Card>
              </div>
            )}

            {currentPage === 'logs' && (
              <Card title="操作日志">
                {logs.length ? (
                  <Table
                    columns={logColumns}
                    dataSource={logs.map((log, idx) => ({ ...log, key: idx }))}
                    pagination={{ pageSize: 20 }}
                    scroll={{ x: 1000 }}
                  />
                ) : (
                  <Empty description="暂无日志数据" />
                )}
              </Card>
            )}

            {currentPage === 'advanced_analytics' && (
              <div>
                <Row gutter={16} style={{ marginBottom: 24 }}>
                  <Col xs={24}>
                    <Card title="热力图：用户活动时间分布">
                      <div id="heatmapChart" style={{ height: 400 }}></div>
                    </Card>
                  </Col>
                </Row>

                <Row gutter={16} style={{ marginBottom: 24 }}>
                  <Col xs={24} lg={12}>
                    <Card title="漏斗图：用户转化流程">
                      <div id="funnelChart" style={{ height: 400 }}></div>
                    </Card>
                  </Col>
                  <Col xs={24} lg={12}>
                    <Card title="散点图：用户活跃度分析">
                      <div id="scatterChart" style={{ height: 400 }}></div>
                    </Card>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col xs={24}>
                    <Card title="树状图：角色用户分布">
                      <div id="treeChart" style={{ height: 400 }}></div>
                    </Card>
                  </Col>
                </Row>
              </div>
            )}

            {currentPage === 'permissions' && (
              <div>
                <Row gutter={16} style={{ marginBottom: 24 }}>
                  <Col xs={24} lg={12}>
                    <Card title="角色列表">
                      {permissions?.roles ? (
                        <div>
                          {permissions.roles.map((role: any) => (
                            <div key={role.id} style={{ marginBottom: 16, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
                              <div style={{ fontSize: 16, fontWeight: 'bold', marginBottom: 4 }}>
                                {role.name === 'admin' && '👑 '}
                                {role.name === 'manager' && '💼 '}
                                {role.name === 'user' && '👤 '}
                                {role.name.toUpperCase()}
                              </div>
                              <div style={{ color: '#666' }}>{role.description}</div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <Empty description="暂无角色数据" />
                      )}
                    </Card>
                  </Col>

                  <Col xs={24} lg={12}>
                    <Card title="权限对应表">
                      {permissions?.role_permissions ? (
                        <div>
                          {Object.entries(permissions.role_permissions).map(([role, perms]: [string, any]) => (
                            <div key={role} style={{ marginBottom: 16 }}>
                              <div style={{ fontWeight: 'bold', marginBottom: 8, color: '#1890ff' }}>
                                {role.toUpperCase()}
                              </div>
                              <div style={{ paddingLeft: 16 }}>
                                {perms.map((perm: string) => (
                                  <div key={perm} style={{ color: '#666', marginBottom: 4 }}>
                                    ✓ {perm}
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <Empty description="暂无权限数据" />
                      )}
                    </Card>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col xs={24}>
                    <Card title="用户角色分配">
                      <Table
                        columns={[
                          { title: '用户名', dataIndex: 'username', key: 'username', width: 150 },
                          {
                            title: '当前角色',
                            dataIndex: 'role',
                            key: 'role',
                            width: 120,
                            render: (role: string) => <Tag color={role === 'admin' ? 'red' : role === 'manager' ? 'orange' : 'blue'}>{role}</Tag>
                          },
                          {
                            title: '操作',
                            key: 'action',
                            width: 200,
                            render: (_: any, record: any) => (
                              <Space>
                                <Button size="small" type="link" onClick={() => handleChangeRole(record, 'admin')}>设为管理员</Button>
                                <Button size="small" type="link" onClick={() => handleChangeRole(record, 'manager')}>设为经理</Button>
                                <Button size="small" type="link" onClick={() => handleChangeRole(record, 'user')}>设为用户</Button>
                              </Space>
                            )
                          }
                        ]}
                        dataSource={users.map((u, idx) => ({ ...u, key: idx }))}
                        pagination={{ pageSize: 10 }}
                        scroll={{ x: 600 }}
                      />
                    </Card>
                  </Col>
                </Row>
              </div>
            )}
          </Spin>
        </Content>
      </Layout>
    </Layout>
  )
}

export default App
