import './App.css';
import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

import { Layout, Menu, message, Button, Space} from 'antd';
import { Collapse } from 'antd';
import { PlayCircleOutlined, LaptopOutlined } from '@ant-design/icons';
import { Card, Checkbox, Col, Row } from 'antd';
import { Divider } from 'antd';
import { Descriptions } from 'antd';
import { Table } from 'antd';

// import testData from "./testData"
const { Header, Content, Footer } = Layout;
const { Panel } = Collapse;

function findMatchedPerTC(testData, inputSteTC) {
  let matchedDict = {};
  
  for (let TC of inputSteTC){
    matchedDict[TC] = new Set();
  }
  for (let B2B of testData[0].info){
    for (let TC of B2B.details.analysis){
      for (let matchedTCL of TC.tcl.match){
        if (B2B.details.tclData[TC.testCase][matchedTCL] === true) {
          matchedDict[TC.testCase].add(matchedTCL);
        }
      } 
    }
  }
  for (let TC of inputSteTC){
    matchedDict[TC] = Array.from(matchedDict[TC])
  }
  return matchedDict
}

function initSelectedPerTC(inputSteTC){
  let selectedPerTC = {};
  for (let TC of inputSteTC){
    selectedPerTC[TC] = [];
  }
  return selectedPerTC;
}

function isIncludeB2B(B2B, inputSteTC, selectedPerTC) {
  for (let TC of inputSteTC) {
    for (let TCL of selectedPerTC[TC]) {
      if (!(Object.keys(B2B.details.tclData[TC]).includes(TCL) && 
        B2B.details.tclData[TC][TCL] === true)) {
          return false;
        }
    }
  }
  return true;
}

function findMatchedB2Bs(testData, inputSteTC, selectedPerTC){
  let DisplayedB2BList = [];
  for (let B2Bidx in testData[0].info){
    let B2B = testData[0].info[B2Bidx];
    if (isIncludeB2B(B2B, inputSteTC, selectedPerTC) === true) {
      DisplayedB2BList.push(B2Bidx);
    }
  }
  return DisplayedB2BList;
}

function makeTableData(testData, resultB2BList) {
  let tableData = [];
  for (let B2Bidx of resultB2BList) {
    let row = {};
    row['key'] = B2Bidx; 
    row['name'] = testData[0].info[B2Bidx].name;
    row['score'] = testData[0].info[B2Bidx].score;
    tableData.push(row);
  }
  return tableData;
}

function ShowResult() {
  // Create a state variable to store the conktents of the zip file
  const navigate = useNavigate();
  const { state } = useLocation();
  const [table, setTable] = useState(null);

  const testData = state;

  const menuItem = [
    {label: 'Dashboard', icon: React.createElement(PlayCircleOutlined)}, 
    {label: 'Result', icon: React.createElement(LaptopOutlined)}
  ];

  const cardStyle = {
    width: '100%', 
    height: 300
  };

  const bodyStyle = {
    maxHeight: '80%',
    // overflow: "auto"
  };

  const showInfo = () => {
    let input = {};
    let tcNameList = {};
    let isB2B = Boolean();
    
    input = testData[0].input;
    tcNameList = Object.keys(input.tclData);
    tcNameList.sort();

    return (
      <>
        <Descriptions.Item label="Name" span={2}>
          {input.name}
        </Descriptions.Item>
        <Descriptions.Item label="Number of test case">
          {tcNameList.length}
        </Descriptions.Item>
        <Descriptions.Item label="Name of test case" span={2}>
          {tcNameList.map((name, _) => (
            <Col key={name}>
              {name}
            </Col>
          ))}
        </Descriptions.Item>
        {isB2B && (
          <Descriptions.Item label="Score">
            {input.score}
          </Descriptions.Item>
        )}
      </>
    );
  };

  const onClickDetail = (e, B2B) => {
    navigate(`/Result/${B2B.key}`, { state: testData });
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
    },
    {
      title: 'Score',
      dataIndex: 'score',
      defaultSortOrder: 'descend',
      sorter: (a, b) => a.score - b.score,
    },
    {
      title: 'Action',
      key: 'action',
      render: (_, B2B) => (
        <Space size="middle">
          <a onClick={(e) => onClickDetail(e, B2B)}>Detail</a>
          <a>Download</a>
        </Space>
      ),
    },
  ];

  const inputSteTC = Object.keys(testData[0].input.tclData);
  const matchedPerTC = findMatchedPerTC(testData, inputSteTC);
  const selectedPerTC = initSelectedPerTC(inputSteTC);
  
  let tableData = {};

  useEffect(() => {
    tableData = makeTableData(testData, findMatchedB2Bs(testData, inputSteTC, selectedPerTC))
    setTable(tableData);
  }, []);

  const onChange = (TC, checkedValues) => {
    selectedPerTC[TC] = checkedValues;
    tableData = makeTableData(testData, findMatchedB2Bs(testData, inputSteTC, selectedPerTC))
    console.log(selectedPerTC)
    setTable(tableData);
  };

  console.log(testData)

  return (
    <>
      <Layout className="layout">
        <Header
          style={{ backgroundColor: "#2185D0" }}
        >
          <div className="logo" />
          <Menu
            style={{ backgroundColor: "#2185D0", color: "#D0D0D0" }}
            mode="horizontal"
            defaultSelectedKeys={['1']}
            items={menuItem}
          />
        </Header>
        <Layout style={{ minHeight: '80vh' }}>
          <Content style={{ padding: '1% 3%' }}>
            <div className="site-card-wrapper" style={{ padding: '2% 5%' }}>
              <>
                <Space direction="vertical" size="middle" style={{ display: 'flex' }}>
                  <Card
                    style={{
                      width: '100%',
                      height: 250,
                      maxHeight: 250,
                      padding: '1% 3%',
                      overflow: "auto"
                    }}
                    bodyStyle={bodyStyle}
                  >
                    <Space direction="vertical" size="middle" style={{ display: 'flex' }}>
                      <Descriptions title="Input test suite information" bordered>
                        {showInfo()}
                      </Descriptions>
                    </Space>
                  </Card>
                  <Collapse>
                    <Panel
                      header="Select most important Tcl variables"
                      key="1"
                    >
                      <div
                        style={{
                          padding: '1% 3%',
                        }}
                      >
                        {inputSteTC.map((TC, _) => (
                          <>
                            <Divider
                              orientation="left"
                              key={TC}
                            >
                              {TC}
                            </Divider>
                            <Checkbox.Group style={{ width: '100%' }} onChange={(e) => onChange(TC, e)}>
                              <Row gutter={16}>
                                {matchedPerTC[TC].map((TCL, _) => (
                                  <Col span={8} key={TCL}>
                                    <Checkbox value={TCL}>{TCL}</Checkbox>
                                  </Col>
                                ))}
                              </Row>
                            </Checkbox.Group>
                          </>
                        ))}
                      </div>
                    </Panel>
                  </Collapse>
                  <Card
                    title="Similar CI test suites"
                    style={{
                      width: '100%',
                      height: 800,
                      maxHeight: 800,
                      padding: '1% 3%',
                      overflow: "auto"
                    }}
                    bodyStyle={bodyStyle}
                  >
                    {table && (
                      <Table columns={columns} dataSource={table} />
                    )}
                  </Card>
                </Space>
              </>
            </div>
          </Content>
        </Layout>
        <Footer style={{ textAlign: 'center' }}>©2023 Spirent Communications, Inc. All rights reserved.</Footer>
      </Layout>
    </>
  );
}

export default ShowResult;