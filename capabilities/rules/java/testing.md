# Java 测试规则

## 单元测试
- Service 层覆盖率 ≥ 80%
- 使用 JUnit 5 + Mockito
- 测试方法命名：should_预期行为_when_条件
- 每个测试方法只测一个行为

## 测试结构
```java
@Test
void should_return_user_when_id_exists() {
    // Given
    when(userRepository.findById(1L)).thenReturn(Optional.of(user));
    
    // When
    User result = userService.getUser(1L);
    
    // Then
    assertThat(result).isNotNull();
    assertThat(result.getName()).isEqualTo("test");
}
```

## 集成测试
- 使用 @SpringBootTest + @Transactional（自动回滚）
- 数据库测试使用 H2 或 Testcontainers
- API 测试使用 MockMvc 或 RestAssured
- 避免依赖外部服务，使用 Mock 或 WireMock

## 测试数据
- 使用 @BeforeEach 准备测试数据
- 避免测试间依赖，每个测试独立
- 使用 Builder 模式构造复杂对象
- 禁止硬编码 ID，使用动态生成

## 断言规范
- 使用 AssertJ（assertThat）而非 JUnit 原生断言
- 断言要具体：检查字段值，而非仅检查非空
- 异常测试使用 assertThrows，检查异常类型和消息
- 避免使用 System.out.println 验证，使用断言
